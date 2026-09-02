import 'package:flutter/material.dart';
import '../models/governance.dart';

class GovernanceRadarModal extends StatelessWidget {
  final GovernanceRadarReport report;
  final Function(String waiverId, String role) onSignWaiver;
  final VoidCallback onExportAuditBundle;
  final bool isReadOnly;

  const GovernanceRadarModal({
    Key? key,
    required this.report,
    required this.onSignWaiver,
    required this.onExportAuditBundle,
    this.isReadOnly = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
      child: Container(
        width: 800,
        constraints: const BoxConstraints(maxHeight: 700),
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF137333).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.shield_outlined, color: Color(0xFF137333), size: 24),
                ),
                const SizedBox(width: 12),
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Enterprise AI Governance Radar & Compliance Audit',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      'Model Armor DLP • Sovereign Cloud Residency • Dual-Custody Attestation Waivers',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const Divider(height: 32),

            // Top Metric Cards Grid
            Row(
              children: [
                _buildMetricCard(
                  title: 'Overall Governance Score',
                  value: '${(report.overallComplianceScore * 100).toInt()}%',
                  icon: Icons.verified_user,
                  color: const Color(0xFF137333),
                ),
                const SizedBox(width: 12),
                _buildMetricCard(
                  title: 'RAG Grounding Fidelity',
                  value: '${(report.ragGroundingFidelity * 100).toInt()}%',
                  icon: Icons.model_training,
                  color: const Color(0xFF1A73E8),
                ),
                const SizedBox(width: 12),
                _buildMetricCard(
                  title: 'Sovereign Residency',
                  value: report.sovereignResidencyCompliant ? 'Compliant' : 'Non-Compliant',
                  subtitle: report.sovereignRegion,
                  icon: Icons.public,
                  color: const Color(0xFF8E24AA),
                ),
                const SizedBox(width: 12),
                _buildMetricCard(
                  title: 'OSS Licenses Cleared',
                  value: report.ossLicensesCleared ? 'Apache-2.0 / MIT' : 'Blocked',
                  icon: Icons.gavel,
                  color: const Color(0xFFE37400),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Deficit Attestation Waivers Section
            const Text(
              'Active Deficit Attestation Waivers (Dual-Custody Approvals)',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(height: 8),

            Expanded(
              child: report.waivers.isEmpty
                  ? Container(
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: Colors.grey.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text('No active deficit waivers for this workspace. 100% Floor Compliant.'),
                    )
                  : ListView.builder(
                      itemCount: report.waivers.length,
                      itemBuilder: (context, index) {
                        final w = report.waivers[index];
                        final hasGM = w.productGmApprover != null && w.productGmApprover!.isNotEmpty;
                        final hasLegal = w.legalCounselApprover != null && w.legalCounselApprover!.isNotEmpty;

                        return Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.grey.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: Colors.grey.withOpacity(0.2)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    w.featureName,
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                  ),
                                  const SizedBox(width: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFE8F0FE),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      w.currentStatus,
                                      style: const TextStyle(color: Color(0xFF1A73E8), fontSize: 10, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                  const Spacer(),
                                  Text(
                                    'Target GA: ${w.targetGaDate}',
                                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Mitigation: ${w.fallbackMitigation}',
                                style: const TextStyle(fontSize: 12),
                              ),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  _buildSignatureBadge('Product GM Approval', hasGM, w.productGmApprover),
                                  const SizedBox(width: 12),
                                  _buildSignatureBadge('Corporate Legal Approval', hasLegal, w.legalCounselApprover),
                                  const Spacer(),
                                  if (!hasGM && !isReadOnly)
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(0xFF1A73E8),
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      ),
                                      onPressed: () => onSignWaiver(w.waiverId, 'PRODUCT_GM'),
                                      child: const Text('Sign as GM', style: TextStyle(fontSize: 11, color: Colors.white)),
                                    ),
                                  if (!hasLegal && !isReadOnly) ...[
                                    const SizedBox(width: 8),
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(0xFF137333),
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      ),
                                      onPressed: () => onSignWaiver(w.waiverId, 'LEGAL_COUNSEL'),
                                      child: const Text('Sign as Legal', style: TextStyle(fontSize: 11, color: Colors.white)),
                                    ),
                                  ],
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
            const SizedBox(height: 16),

            // Footer Actions
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                OutlinedButton.icon(
                  icon: const Icon(Icons.download, size: 16),
                  label: const Text('Export Cryptographic Audit Bundle'),
                  onPressed: onExportAuditBundle,
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1A73E8)),
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Done', style: TextStyle(color: Colors.white)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    String? subtitle,
    required IconData icon,
    required Color color,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 16, color: color),
                const Spacer(),
              ],
            ),
            const SizedBox(height: 8),
            Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
            const SizedBox(height: 2),
            Text(title, style: const TextStyle(fontSize: 11, color: Colors.grey)),
            if (subtitle != null) ...[
              const SizedBox(height: 2),
              Text(subtitle, style: TextStyle(fontSize: 10, color: color.withOpacity(0.8))),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSignatureBadge(String title, bool isSigned, String? approver) {
    return Row(
      children: [
        Icon(
          isSigned ? Icons.check_circle : Icons.radio_button_unchecked,
          size: 14,
          color: isSigned ? const Color(0xFF137333) : Colors.grey,
        ),
        const SizedBox(width: 4),
        Text(
          isSigned ? '$title ($approver)' : '$title (Pending)',
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSigned ? FontWeight.bold : FontWeight.normal,
            color: isSigned ? const Color(0xFF137333) : Colors.grey.shade600,
          ),
        ),
      ],
    );
  }
}
