# Material Facts 템플릿

## 1. 목적

판례 비교에서 가장 중요한 것은 결과가 다르다는 사실보다, 사실관계가 논리적으로 얼마나 유사한지다. material facts는 법률 판단에 영향을 주는 핵심 사실 요소를 구조화한 것이다.

## 2. 공통 스키마

모든 손해배상 판례는 가능한 한 아래 공통 필드를 가진다.

```json
{
  "event_type": null,
  "legal_domain": "손해배상",
  "claim_type": null,
  "plaintiff_type": null,
  "defendant_type": null,
  "relationship_between_parties": null,
  "defendant_conduct": null,
  "plaintiff_conduct": null,
  "harm_type": null,
  "harm_severity": null,
  "causation_dispute": null,
  "negligence_dispute": null,
  "damage_scope_dispute": null,
  "evidence_issue": null,
  "key_disputed_fact": null
}
```

## 3. 교통사고 템플릿

```json
{
  "event_type": "교통사고",
  "accident_type": null,
  "victim_status": null,
  "defendant_vehicle_type": null,
  "plaintiff_vehicle_type": null,
  "road_context": null,
  "traffic_signal_issue": null,
  "speeding_issue": null,
  "defendant_conduct": null,
  "victim_conduct": null,
  "injury_type": null,
  "injury_severity": null,
  "causation_dispute": null,
  "negligence_offset_issue": null,
  "negligence_ratio": null,
  "insurance_status": null,
  "damage_scope_issue": null,
  "key_disputed_fact": null
}
```

비교에서 중요한 미세 차이:

- 피해자의 무단횡단 여부
- 신호 위반 여부
- 운전자의 전방주시 의무 위반 정도
- 사고 당시 속도
- 피해자 보호 필요성
- 인과관계 단절 주장 여부
- 과실상계 비율

## 4. 사용자책임 템플릿

```json
{
  "event_type": "사용자책임",
  "employee_status": null,
  "employment_relationship_disputed": null,
  "act_within_scope_of_work": null,
  "defendant_supervision_issue": null,
  "employee_conduct": null,
  "victim_harm": null,
  "causation_dispute": null,
  "employer_exemption_argument": null,
  "key_disputed_fact": null
}
```

비교에서 중요한 미세 차이:

- 사용관계 인정 여부
- 사무집행 관련성
- 사용자의 선임/감독상 과실
- 피용자의 독자적 일탈행위 여부

## 5. 공동불법행위 템플릿

```json
{
  "event_type": "공동불법행위",
  "number_of_tortfeasors": null,
  "common_intent_or_relation": null,
  "separate_acts_combined": null,
  "indivisible_damage": null,
  "causation_between_each_act_and_damage": null,
  "liability_allocation_issue": null,
  "key_disputed_fact": null
}
```

비교에서 중요한 미세 차이:

- 공동성 인정 여부
- 각 행위와 손해 사이 인과관계
- 손해의 불가분성
- 책임 분담 가능성

## 6. 위자료 템플릿

```json
{
  "event_type": "위자료",
  "non_property_damage_type": null,
  "mental_distress_context": null,
  "victim_status": null,
  "defendant_fault_degree": null,
  "harm_duration": null,
  "social_status_or_relationship": null,
  "amount_awarded": null,
  "amount_reasoning_factor": null,
  "key_disputed_fact": null
}
```

비교에서 중요한 미세 차이:

- 피해 정도
- 고의/과실 정도
- 정신적 고통의 기간
- 기존 관계
- 인정 금액 산정 요소

## 7. 과실상계 템플릿

```json
{
  "event_type": "과실상계",
  "plaintiff_fault": null,
  "defendant_fault": null,
  "plaintiff_fault_contributed_to_damage": null,
  "foreseeability_issue": null,
  "negligence_ratio": null,
  "reason_for_ratio": null,
  "damage_reduction_result": null,
  "key_disputed_fact": null
}
```

비교에서 중요한 미세 차이:

- 피해자의 주의의무 위반
- 피해자 행위와 손해 확대 사이 인과관계
- 과실비율 산정 근거
- 손해 확대 방지 가능성

## 8. 향후 형사 도메인 확장 시 필드

형사 사건은 사소한 차이가 죄의 성립, 죄질, 양형을 크게 바꾼다. 확장 시 다음 필드를 별도로 둔다.

```json
{
  "crime_type": null,
  "intent_level": null,
  "weapon_used": null,
  "injury_severity": null,
  "victim_vulnerability": null,
  "prior_record": null,
  "provocation": null,
  "settlement": null,
  "confession": null,
  "recidivism_period": null,
  "aggravating_factors": [],
  "mitigating_factors": []
}
```

## 9. 추출 규칙

- 원문에 명시된 사실만 채운다.
- 불명확한 필드는 null로 둔다.
- 추론이 필요한 필드는 confidence를 낮춘다.
- 각 material fact는 가능한 evidence span을 가져야 한다.
- 비교 점수 계산에서는 null 필드를 과도하게 벌점 처리하지 않는다.

