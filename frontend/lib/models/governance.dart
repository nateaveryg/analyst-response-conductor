class DeficitAttestationWaiver {
  final String waiverId;
  final String workspaceId;
  final String featureName;
  final String currentStatus;
  final String targetGaDate;
  final String fallbackMitigation;
  final String? productGmApprover;
  final String? legalCounselApprover;
  final bool isApproved;
  final String manifestSha256;

  DeficitAttestationWaiver({
    required this.waiverId,
    required this.workspaceId,
    required this.featureName,
    required this.currentStatus,
    required this.targetGaDate,
    required this.fallbackMitigation,
    this.productGmApprover,
    this.legalCounselApprover,
    required this.isApproved,
    required this.manifestSha256,
  });

  factory DeficitAttestationWaiver.fromJson(Map<String, dynamic> json) => DeficitAttestationWaiver(
    waiverId: json['waiver_id'] ?? '',
    workspaceId: json['workspace_id'] ?? '',
    featureName: json['feature_name'] ?? '',
    currentStatus: json['current_status'] ?? 'PUBLIC_PREVIEW',
    targetGaDate: json['target_ga_date'] ?? '',
    fallbackMitigation: json['fallback_mitigation'] ?? '',
    productGmApprover: json['product_gm_approver'],
    legalCounselApprover: json['legal_counsel_approver'],
    isApproved: json['is_approved'] ?? false,
    manifestSha256: json['manifest_sha256'] ?? '',
  );
}

class GovernanceRadarReport {
  final String workspaceId;
  final double overallComplianceScore;
  final double ragGroundingFidelity;
  final int activeWaiversCount;
  final bool waiversApproved;
  final bool sovereignResidencyCompliant;
  final String sovereignRegion;
  final bool ossLicensesCleared;
  final bool commercialRatesVerified;
  final List<DeficitAttestationWaiver> waivers;

  GovernanceRadarReport({
    required this.workspaceId,
    required this.overallComplianceScore,
    required this.ragGroundingFidelity,
    required this.activeWaiversCount,
    required this.waiversApproved,
    required this.sovereignResidencyCompliant,
    required this.sovereignRegion,
    required this.ossLicensesCleared,
    required this.commercialRatesVerified,
    required this.waivers,
  });

  factory GovernanceRadarReport.fromJson(Map<String, dynamic> json) {
    var rawWaivers = json['waivers'] as List? ?? [];
    return GovernanceRadarReport(
      workspaceId: json['workspace_id'] ?? '',
      overallComplianceScore: (json['overall_compliance_score'] as num?)?.toDouble() ?? 0.0,
      ragGroundingFidelity: (json['rag_grounding_fidelity'] as num?)?.toDouble() ?? 0.0,
      activeWaiversCount: json['active_waivers_count'] ?? 0,
      waiversApproved: json['waivers_approved'] ?? false,
      sovereignResidencyCompliant: json['sovereign_residency_compliant'] ?? true,
      sovereignRegion: json['sovereign_region'] ?? 'europe-west3',
      ossLicensesCleared: json['oss_licenses_cleared'] ?? true,
      commercialRatesVerified: json['commercial_rates_verified'] ?? true,
      waivers: rawWaivers.map((w) => DeficitAttestationWaiver.fromJson(w)).toList(),
    );
  }
}
