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

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type FlowEvent struct {
	Timestamp int64  `json:"timestamp"`
	SrcIP     string `json:"src_ip"`
	SrcPort   int    `json:"src_port"`
	DestIP    string `json:"dest_ip"`
	DestPort  int    `json:"dest_port"`
	Protocol  string `json:"protocol"`
	SNIDomain string `json:"sni_domain"`
	Status    string `json:"status"`
}

var (
	flowsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "sentinel_flows_total", Help: "Total flows by status",
	}, []string{"status"})
	sniDomainsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "sentinel_sni_domains_total", Help: "SNI domains seen",
	}, []string{"domain"})
	activeConnections = prometheus.NewGauge(prometheus.GaugeOpts{
		Name: "sentinel_active_connections", Help: "Active IPC connections",
	})
	eventsProcessed = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "sentinel_events_processed_total", Help: "Total events processed",
	})
)

func init() {
	prometheus.MustRegister(flowsTotal, sniDomainsTotal, activeConnections, eventsProcessed)
}

type RateLimiter struct {
	mu      sync.Mutex
	windows map[string][]time.Time
	limit   int
	window  time.Duration
}

func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	return &RateLimiter{windows: make(map[string][]time.Time), limit: limit, window: window}
}

func (r *RateLimiter) Allow(ip string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	now := time.Now()
	cutoff := now.Add(-r.window)
	times := r.windows[ip]
	valid := times[:0]
	for _, t := range times {
		if t.After(cutoff) {
			valid = append(valid, t)
		}
	}
	valid = append(valid, now)
	r.windows[ip] = valid
	return len(valid) <= r.limit
}

type WorkerPool struct {
	jobs    chan FlowEvent
	wg      sync.WaitGroup
	limiter *RateLimiter
	blocked atomic.Int64
}

func NewWorkerPool(workers int, limiter *RateLimiter) *WorkerPool {
	p := &WorkerPool{jobs: make(chan FlowEvent, 10000), limiter: limiter}
	for i := 0; i < workers; i++ {
		p.wg.Add(1)
		go p.worker()
	}
	return p
}

func (p *WorkerPool) Submit(evt FlowEvent) { p.jobs <- evt }

func (p *WorkerPool) worker() {
	defer p.wg.Done()
	for evt := range p.jobs {
		eventsProcessed.Inc()
		flowsTotal.WithLabelValues(evt.Status).Inc()
		if evt.SNIDomain != "" {
			sniDomainsTotal.WithLabelValues(evt.SNIDomain).Inc()
			log.Printf("[CONTROL] SNI=%-30s src=%s:%d -> %s:%d",
				evt.SNIDomain, evt.SrcIP, evt.SrcPort, evt.DestIP, evt.DestPort)
		}
		if !p.limiter.Allow(evt.SrcIP) {
			p.blocked.Add(1)
			log.Printf("[THREAT] RATE_LIMIT src=%s total_blocked=%d", evt.SrcIP, p.blocked.Load())
		}
	}
}

func (p *WorkerPool) Stop() { close(p.jobs); p.wg.Wait() }

func handleConn(conn net.Conn, pool *WorkerPool) {
	defer func() { conn.Close(); activeConnections.Dec() }()
	log.Printf("[CONTROL] C++ engine connected")
	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" { continue }
		var evt FlowEvent
		if err := json.Unmarshal([]byte(line), &evt); err != nil { continue }
		pool.Submit(evt)
	}
}

func serveSocket(socketPath string, pool *WorkerPool) {
	os.Remove(socketPath)
	ln, err := net.Listen("unix", socketPath)
	if err != nil { log.Fatalf("[CONTROL] Listen failed: %v", err) }
	defer ln.Close()
	log.Printf("[CONTROL] Listening on %s", socketPath)
	for {
		conn, err := ln.Accept()
		if err != nil { continue }
		activeConnections.Inc()
		go handleConn(conn, pool)
	}
}

func main() {
	socketPath := "/tmp/axiom_sentinel.sock"
	if len(os.Args) > 1 { socketPath = os.Args[1] }
	log.Printf("[CONTROL] Axiom Sentinel Control Plane v1.0")
	log.Printf("[CONTROL] Socket: %s", socketPath)
	log.Printf("[CONTROL] Metrics: http://localhost:9182/metrics")
	limiter := NewRateLimiter(1000, time.Minute)
	pool := NewWorkerPool(8, limiter)
	defer pool.Stop()
	go func() {
		http.Handle("/metrics", promhttp.Handler())
		http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
			fmt.Fprintf(w, `{"status":"ok","service":"sentinel-control-plane"}`)
		})
		log.Fatal(http.ListenAndServe(":9182", nil))
	}()
	serveSocket(socketPath, pool)
}
