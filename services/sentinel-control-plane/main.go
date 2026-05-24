package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gomodule/redigo/redis"
	geoip2 "github.com/oschwald/geoip2-golang"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type FlowEvent struct {
	Timestamp  int64  `json:"timestamp"`
	SrcIP      string `json:"src_ip"`
	SrcPort    int    `json:"src_port"`
	DestIP     string `json:"dest_ip"`
	DestPort   int    `json:"dest_port"`
	Protocol   string `json:"protocol"`
	SNIDomain  string `json:"sni_domain"`
	Status     string `json:"status"`
	DeviceType string `json:"device_type"`
	HospitalID string `json:"hospital_id"`
}

type ThreatEvent struct {
	Timestamp  time.Time `json:"timestamp"`
	SrcIP      string    `json:"src_ip"`
	DestIP     string    `json:"dest_ip"`
	ThreatType string    `json:"threat_type"`
	Severity   string    `json:"severity"`
	Detail     string    `json:"detail"`
	SNIDomain  string    `json:"sni_domain"`
}

var (
	flowsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "sentinel_flows_total", Help: "Flows by status",
	}, []string{"status"})
	threatsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "sentinel_threats_detected_total", Help: "Threats by severity",
	}, []string{"severity", "type"})
	sniTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "sentinel_sni_domains_total", Help: "SNI domains seen",
	}, []string{"domain"})
	activeConns = prometheus.NewGauge(prometheus.GaugeOpts{
		Name: "sentinel_active_connections", Help: "Active IPC connections",
	})
	eventsProcessed = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "sentinel_events_processed_total", Help: "Events processed",
	})
	blockedIPsGauge = prometheus.NewGauge(prometheus.GaugeOpts{
		Name: "sentinel_blocked_ips_active", Help: "Blocked IPs",
	})
)

func init() {
	prometheus.MustRegister(flowsTotal, threatsTotal, sniTotal,
		activeConns, eventsProcessed, blockedIPsGauge)
}

var (
	globalThreats []ThreatEvent
	threatsMu     sync.RWMutex
	threatsChan   = make(chan ThreatEvent, 1000)
	redisPool     *redis.Pool
)

func redisSet(key, val string, ttl int) {
	if redisPool == nil {
		return
	}
	c := redisPool.Get()
	defer c.Close()
	c.Do("SETEX", key, ttl, val)
}

// GeoIP
type GeoPool struct {
	db      *geoip2.Reader
	allowed map[string]bool
}

func NewGeoPool(path string) *GeoPool {
	db, err := geoip2.Open(path)
	if err != nil {
		log.Printf("[GEOIP] Warning: %v", err)
		return &GeoPool{allowed: map[string]bool{"IN": true, "US": true, "GB": true, "AE": true, "OM": true}}
	}
	log.Printf("[GEOIP] GeoLite2-Country loaded")
	return &GeoPool{db: db, allowed: map[string]bool{"IN": true, "US": true, "GB": true, "AE": true, "OM": true}}
}

func (g *GeoPool) Check(evt FlowEvent) {
	if g.db == nil {
		return
	}
	ip := net.ParseIP(evt.SrcIP)
	if ip == nil {
		return
	}
	rec, err := g.db.Country(ip)
	if err != nil || rec.Country.IsoCode == "" {
		return
	}
	code := rec.Country.IsoCode
	if !g.allowed[code] {
		t := ThreatEvent{
			Timestamp: time.Now(), SrcIP: evt.SrcIP, DestIP: evt.DestIP,
			ThreatType: "GEO_BLOCK", Severity: "MEDIUM",
			Detail: fmt.Sprintf("Traffic from blocked country: %s", code),
		}
		log.Printf("[GEOIP] BLOCKED country=%s src=%s", code, evt.SrcIP)
		threatsTotal.WithLabelValues("MEDIUM", "GEO_BLOCK").Inc()
		select {
		case threatsChan <- t:
		default:
		}
	}
}

// Rate limiter
type RateLimiter struct {
	mu      sync.Mutex
	packets map[string][]time.Time
	ports   map[string]map[int]bool
	blocked atomic.Int64
}

func NewRateLimiter() *RateLimiter {
	return &RateLimiter{
		packets: make(map[string][]time.Time),
		ports:   make(map[string]map[int]bool),
	}
}

func (r *RateLimiter) Check(evt FlowEvent) {
	r.mu.Lock()
	defer r.mu.Unlock()
	now := time.Now()
	cutoff := now.Add(-10 * time.Second)
	ip := evt.SrcIP
	times := r.packets[ip]
	valid := times[:0]
	for _, t := range times {
		if t.After(cutoff) {
			valid = append(valid, t)
		}
	}
	valid = append(valid, now)
	r.packets[ip] = valid
	if len(valid) > 100 {
		r.blocked.Add(1)
		blockedIPsGauge.Set(float64(r.blocked.Load()))
		t := ThreatEvent{
			Timestamp: now, SrcIP: ip, DestIP: evt.DestIP,
			ThreatType: "SYN_FLOOD", Severity: "HIGH",
			Detail: fmt.Sprintf("SYN flood: %d packets/10s", len(valid)),
		}
		log.Printf("[RATELIMIT] SYN_FLOOD src=%s count=%d", ip, len(valid))
		threatsTotal.WithLabelValues("HIGH", "SYN_FLOOD").Inc()
		redisSet(fmt.Sprintf("sentinel:blocked:%s", ip), "1", 3600)
		go func(ip string) {
			log.Printf("[IPTABLES] Would block %s (simulated)", ip)
		}(ip)
		select {
		case threatsChan <- t:
		default:
		}
	}
	if r.ports[ip] == nil {
		r.ports[ip] = make(map[int]bool)
	}
	r.ports[ip][evt.DestPort] = true
	if len(r.ports[ip]) > 20 {
		t := ThreatEvent{
			Timestamp: now, SrcIP: ip, DestIP: evt.DestIP,
			ThreatType: "PORT_SCAN", Severity: "MEDIUM",
			Detail: fmt.Sprintf("Port scan: %d distinct ports", len(r.ports[ip])),
		}
		log.Printf("[RATELIMIT] PORT_SCAN src=%s ports=%d", ip, len(r.ports[ip]))
		threatsTotal.WithLabelValues("MEDIUM", "PORT_SCAN").Inc()
		r.ports[ip] = make(map[int]bool)
		select {
		case threatsChan <- t:
		default:
		}
	}
}

// SNI Intel
type SNIIntel struct {
	blocklist map[string]bool
	allowlist map[string]bool
}

func NewSNIIntel() *SNIIntel {
	return &SNIIntel{
		blocklist: map[string]bool{
			"malware.example.com": true, "c2server.example.com": true,
		},
		allowlist: map[string]bool{
			"epic.com": true, "cerner.com": true, "github.com": true,
			"google.com": true, "stackoverflow.com": true,
		},
	}
}

func (s *SNIIntel) Check(evt FlowEvent) {
	if evt.SNIDomain == "" {
		return
	}
	sniTotal.WithLabelValues(evt.SNIDomain).Inc()
	if s.blocklist[evt.SNIDomain] {
		t := ThreatEvent{
			Timestamp: time.Now(), SrcIP: evt.SrcIP, DestIP: evt.DestIP,
			ThreatType: "MALICIOUS_DOMAIN", Severity: "CRITICAL",
			SNIDomain: evt.SNIDomain,
			Detail:    fmt.Sprintf("Malicious domain: %s", evt.SNIDomain),
		}
		log.Printf("[SNI] CRITICAL domain=%s src=%s", evt.SNIDomain, evt.SrcIP)
		threatsTotal.WithLabelValues("CRITICAL", "MALICIOUS_DOMAIN").Inc()
		select {
		case threatsChan <- t:
		default:
		}
		return
	}
	if evt.DeviceType == "medical_device" && !s.allowlist[evt.SNIDomain] {
		t := ThreatEvent{
			Timestamp: time.Now(), SrcIP: evt.SrcIP, DestIP: evt.DestIP,
			ThreatType: "UNEXPECTED_DOMAIN", Severity: "MEDIUM",
			SNIDomain: evt.SNIDomain,
			Detail:    fmt.Sprintf("Medical device->unlisted domain: %s", evt.SNIDomain),
		}
		log.Printf("[SNI] MEDIUM medical_device domain=%s", evt.SNIDomain)
		threatsTotal.WithLabelValues("MEDIUM", "UNEXPECTED_DOMAIN").Inc()
		select {
		case threatsChan <- t:
		default:
		}
	}
}

// Trust scorer
type TrustScorer struct {
	mu     sync.Mutex
	scores map[string]float64
}

func NewTrustScorer() *TrustScorer {
	return &TrustScorer{scores: make(map[string]float64)}
}

func (t *TrustScorer) Penalise(ip, severity string) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if _, ok := t.scores[ip]; !ok {
		t.scores[ip] = 1.0
	}
	switch severity {
	case "MEDIUM":
		t.scores[ip] -= 0.1
	case "HIGH":
		t.scores[ip] -= 0.3
	case "CRITICAL":
		t.scores[ip] -= 0.5
	}
	if t.scores[ip] < 0 {
		t.scores[ip] = 0
	}
	log.Printf("[TRUST] ip=%s score=%.2f", ip, t.scores[ip])
	redisSet(fmt.Sprintf("sentinel:trust:%s", ip),
		fmt.Sprintf("%.2f", t.scores[ip]), 86400)
}

func threatCollector(scorer *TrustScorer) {
	for threat := range threatsChan {
		threatsMu.Lock()
		if len(globalThreats) > 10000 {
			globalThreats = globalThreats[1:]
		}
		globalThreats = append(globalThreats, threat)
		threatsMu.Unlock()
		scorer.Penalise(threat.SrcIP, threat.Severity)
	}
}

func processEvent(evt FlowEvent, geo *GeoPool, rate *RateLimiter, sni *SNIIntel) {
	eventsProcessed.Inc()
	flowsTotal.WithLabelValues(evt.Status).Inc()
	geo.Check(evt)
	rate.Check(evt)
	sni.Check(evt)
}

func handleConn(conn net.Conn, geo *GeoPool, rate *RateLimiter, sni *SNIIntel) {
	defer func() { conn.Close(); activeConns.Dec() }()
	log.Printf("[CONTROL] C++ engine connected")
	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		var evt FlowEvent
		if err := json.Unmarshal([]byte(line), &evt); err != nil {
			continue
		}
		processEvent(evt, geo, rate, sni)
	}
}

func serveSocket(path string, geo *GeoPool, rate *RateLimiter, sni *SNIIntel) {
	os.Remove(path)
	ln, err := net.Listen("unix", path)
	if err != nil {
		log.Fatalf("[CONTROL] Listen failed: %v", err)
	}
	defer ln.Close()
	log.Printf("[CONTROL] Listening on %s", path)
	for {
		conn, err := ln.Accept()
		if err != nil {
			continue
		}
		activeConns.Inc()
		go handleConn(conn, geo, rate, sni)
	}
}

func main() {
	socketPath := "/tmp/axiom_sentinel.sock"
	mmdbPath   := "rules/GeoLite2-Country.mmdb"

	log.Printf("[CONTROL] Axiom Sentinel Control Plane v2.0")

	redisPool = &redis.Pool{
		MaxIdle: 5,
		Dial: func() (redis.Conn, error) {
			return redis.Dial("tcp", "localhost:6380")
		},
	}
	c := redisPool.Get()
	if _, err := c.Do("PING"); err != nil {
		log.Printf("[CONTROL] Redis unavailable: %v", err)
		redisPool = nil
	} else {
		log.Printf("[CONTROL] Redis connected on :6380")
	}
	c.Close()

	geo    := NewGeoPool(mmdbPath)
	rate   := NewRateLimiter()
	sni    := NewSNIIntel()
	scorer := NewTrustScorer()

	go threatCollector(scorer)

	go func() {
		mux := http.NewServeMux()
		mux.Handle("/metrics", promhttp.Handler())
		mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
			fmt.Fprintf(w, `{"status":"ok"}`)
		})
		mux.HandleFunc("/sentinel/threats", func(w http.ResponseWriter, r *http.Request) {
			threatsMu.RLock()
			defer threatsMu.RUnlock()
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"threats": globalThreats, "total": len(globalThreats),
			})
		})
		mux.HandleFunc("/sentinel/stats", func(w http.ResponseWriter, r *http.Request) {
			threatsMu.RLock()
			n := len(globalThreats)
			threatsMu.RUnlock()
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"threats_total": n, "status": "running",
			})
		})
		log.Printf("[CONTROL] API on :8090  Metrics on :9182")
		go http.ListenAndServe(":9182", promhttp.Handler())
		log.Fatal(http.ListenAndServe(":8090", mux))
	}()

	serveSocket(socketPath, geo, rate, sni)
}
