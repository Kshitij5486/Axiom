package com.axiom.fhir.repository;

import com.axiom.fhir.entity.ObservationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface ObservationRepository extends JpaRepository<ObservationEntity, UUID> {
    List<ObservationEntity> findByPatientIdOrderByEffectiveAtDesc(UUID patientId);
}
