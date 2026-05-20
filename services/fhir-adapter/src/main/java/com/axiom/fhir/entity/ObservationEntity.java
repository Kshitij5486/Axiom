package com.axiom.fhir.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "observations")
@Data
@NoArgsConstructor
public class ObservationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "obs_id")
    private UUID obsId;

    @Column(name = "patient_id")
    private UUID patientId;

    @Column(name = "fhir_obs_id")
    private String fhirObsId;

    @Column(name = "category")
    private String category;

    @Column(name = "code")
    private String code;

    @Column(name = "feature_name")
    private String featureName;

    @Column(name = "display")
    private String display;

    @Column(name = "value_quantity")
    private Double valueQuantity;

    @Column(name = "unit")
    private String unit;

    @Column(name = "reference_low")
    private Double referenceLow;

    @Column(name = "reference_high")
    private Double referenceHigh;

    @Column(name = "is_abnormal")
    private Boolean isAbnormal;

    @Column(name = "status")
    private String status;

    @Column(name = "effective_at")
    private LocalDateTime effectiveAt;

    @Column(name = "recorded_at")
    private LocalDateTime recordedAt;

    @PrePersist
    protected void onCreate() {
        recordedAt = LocalDateTime.now();
    }
}
