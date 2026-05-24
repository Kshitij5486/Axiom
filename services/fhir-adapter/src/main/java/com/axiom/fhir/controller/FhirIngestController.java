package com.axiom.fhir.controller;

import ca.uhn.fhir.context.FhirContext;
import ca.uhn.fhir.parser.IParser;
import com.axiom.fhir.entity.ObservationEntity;
import com.axiom.fhir.entity.PatientEntity;
import com.axiom.fhir.repository.ObservationRepository;
import com.axiom.fhir.repository.PatientRepository;
import com.axiom.fhir.service.KafkaProducerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.hl7.fhir.r4.model.Observation;
import org.hl7.fhir.r4.model.Patient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/fhir")
@RequiredArgsConstructor
@Slf4j
public class FhirIngestController {

    private final PatientRepository patientRepo;
    private final ObservationRepository obsRepo;
    private final KafkaProducerService kafkaProducer;
    private final FhirContext fhirContext = FhirContext.forR4();

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "healthy");
        response.put("service", "axiom-fhir-adapter");
        response.put("version", "1.0.0");
        response.put("timestamp", Instant.now().toString());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/patient")
    public ResponseEntity<Map<String, Object>> ingestPatient(
            @RequestBody String fhirJson) {
        try {
            IParser parser = fhirContext.newJsonParser();
            Patient fhirPatient = parser.parseResource(Patient.class, fhirJson);

            PatientEntity entity = new PatientEntity();
            entity.setFhirId(fhirPatient.getIdElement().getIdPart());

            if (!fhirPatient.getName().isEmpty()) {
                var name = fhirPatient.getName().get(0);
                if (!name.getGiven().isEmpty()) {
                    entity.setFirstName(name.getGiven().get(0).getValue());
                }
                entity.setLastName(name.getFamily());
            }

            entity.setGender(fhirPatient.getGender() != null
                ? fhirPatient.getGender().toCode() : "unknown");

            if (fhirPatient.getBirthDate() != null) {
                entity.setDateOfBirth(fhirPatient.getBirthDate()
                    .toInstant()
                    .atZone(java.time.ZoneId.systemDefault())
                    .toLocalDate());
            }

            entity = patientRepo.save(entity);
            log.info("Patient ingested: fhir_id={} patient_id={}",
                entity.getFhirId(), entity.getPatientId());

            Map<String, Object> event = new HashMap<>();
            event.put("event_type", "patient.registered");
            event.put("patient_id", entity.getPatientId().toString());
            event.put("fhir_id", entity.getFhirId());
            event.put("timestamp", Instant.now().toString());
            kafkaProducer.publish("patient.events",
                entity.getPatientId().toString(), event);

            Map<String, Object> response = new HashMap<>();
            response.put("patient_id", entity.getPatientId().toString());
            response.put("fhir_id", entity.getFhirId());
            response.put("status", "ingested");
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("Patient ingest failed: {}", e.getMessage());
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/observation")
    public ResponseEntity<Map<String, Object>> ingestObservation(
            @RequestBody String fhirJson) {
        try {
            IParser parser = fhirContext.newJsonParser();
            Observation fhirObs = parser.parseResource(
                Observation.class, fhirJson);

            ObservationEntity entity = new ObservationEntity();
            entity.setFhirObsId(fhirObs.getIdElement().getIdPart());
            entity.setStatus(fhirObs.getStatus() != null
                ? fhirObs.getStatus().toCode() : "final");

            if (!fhirObs.getCategory().isEmpty()
                    && !fhirObs.getCategory().get(0).getCoding().isEmpty()) {
                entity.setCategory(fhirObs.getCategory()
                    .get(0).getCoding().get(0).getCode());
            }

            if (!fhirObs.getCode().getCoding().isEmpty()) {
                var coding = fhirObs.getCode().getCoding().get(0);
                entity.setCode(coding.getCode());
                entity.setDisplay(coding.getDisplay());
                entity.setFeatureName(
                    loincToFeatureName(coding.getCode())
                );
            }

            if (fhirObs.hasValueQuantity()) {
                entity.setValueQuantity(
                    fhirObs.getValueQuantity().getValue().doubleValue());
                entity.setUnit(fhirObs.getValueQuantity().getUnit());
            }

            String patientRef = fhirObs.getSubject().getReference();
            if (patientRef != null && patientRef.contains("/")) {
                String fhirId = patientRef.split("/")[1];
                patientRepo.findByFhirId(fhirId).ifPresent(p -> {
                    entity.setPatientId(p.getPatientId());
                });
            }

            entity.setEffectiveAt(LocalDateTime.now());
            obsRepo.save(entity);

            Map<String, Object> event = new HashMap<>();
            event.put("patient_id",
                entity.getPatientId() != null
                    ? entity.getPatientId().toString() : "unknown");
            event.put("feature_name", entity.getFeatureName());
            event.put("value", entity.getValueQuantity());
            event.put("unit", entity.getUnit());
            event.put("is_abnormal", entity.getIsAbnormal());
            event.put("timestamp", Instant.now().toString());

            kafkaProducer.publish("patient.vitals",
                entity.getPatientId() != null
                    ? entity.getPatientId().toString() : "unknown",
                event);

            Map<String, Object> response = new HashMap<>();
            response.put("obs_id", entity.getObsId());
            response.put("feature_name", entity.getFeatureName());
            response.put("status", "ingested");
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("Observation ingest failed: {}", e.getMessage());
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    @GetMapping("/patients")
    public ResponseEntity<?> listPatients() {
        return ResponseEntity.ok(patientRepo.findAll());
    }

    private String loincToFeatureName(String loincCode) {
        return switch (loincCode) {
            case "8867-4"  -> "heart_rate";
            case "55284-4" -> "blood_pressure";
            case "2339-0"  -> "glucose";
            case "718-7"   -> "hemoglobin";
            case "2160-0"  -> "creatinine";
            case "2823-3"  -> "potassium";
            case "2951-2"  -> "sodium";
            case "59408-5" -> "spo2";
            case "8310-5"  -> "body_temperature";
            case "85354-9" -> "blood_pressure";
            default        -> loincCode;
        };
    }
}
