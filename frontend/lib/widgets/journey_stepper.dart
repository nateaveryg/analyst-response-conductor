import 'package:flutter/material.dart';

class JourneyStepper extends StatelessWidget {
  final int currentPhase;
  final Function(int phase) onPhaseSelected;

  const JourneyStepper({
    Key? key,
    required this.currentPhase,
    required this.onPhaseSelected,
  }) : super(key: key);

  static const List<Map<String, String>> phases = [
    {'title': 'Phase 1: Criteria Intake', 'desc': 'Criteria & Go/No-Go'},
    {'title': 'Phase 2: Narrative Strategy', 'desc': 'GA Capability Scope'},
    {'title': 'Phase 3: Workback Alignment', 'desc': 'Timeline & Kickoff'},
    {'title': 'Phase 4: Principal TSA RAG', 'desc': '18-Tab RFI Grounding'},
    {'title': 'Phase 5: Demo Sandboxes', 'desc': 'Storyboard Playbook'},
    {'title': 'Phase 6: VP/GM Governance', 'desc': 'Compliance & Waivers'},
    {'title': 'Phase 7: Master Publication', 'desc': 'Manifesto & Delivery'},
  ];

  @override
  Widget build(BuildContext context) {
    final double progress = currentPhase / 7.0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        border: Border(
          bottom: BorderSide(color: Colors.grey.withOpacity(0.2)),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.alt_route, color: Color(0xFF1A73E8), size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'Operational Journey Progress: Phase $currentPhase of 7',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                ],
              ),
              Text(
                '${(progress * 100).toInt()}% Complete',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A73E8),
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: Colors.grey.withOpacity(0.15),
              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF1A73E8)),
              minHeight: 6,
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List.generate(phases.length, (index) {
                final phaseNum = index + 1;
                final isCompleted = phaseNum < currentPhase;
                final isCurrent = phaseNum == currentPhase;

                Color bgColor = Colors.transparent;
                Color borderColor = Colors.grey.withOpacity(0.3);
                Color textColor = Colors.grey.shade700;

                if (isCurrent) {
                  bgColor = const Color(0xFFE8F0FE);
                  borderColor = const Color(0xFF1A73E8);
                  textColor = const Color(0xFF1A73E8);
                } else if (isCompleted) {
                  bgColor = const Color(0xFFE6F4EA);
                  borderColor = const Color(0xFF137333);
                  textColor = const Color(0xFF137333);
                }

                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: InkWell(
                    onTap: () => onPhaseSelected(phaseNum),
                    borderRadius: BorderRadius.circular(20),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: bgColor,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: borderColor),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (isCompleted)
                            const Icon(Icons.check_circle, size: 14, color: Color(0xFF137333))
                          else
                            Container(
                              width: 16,
                              height: 16,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: isCurrent ? const Color(0xFF1A73E8) : Colors.grey.shade400,
                              ),
                              child: Text(
                                '$phaseNum',
                                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                              ),
                            ),
                          const SizedBox(width: 6),
                          Text(
                            phases[index]['title']!,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                              color: textColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }
}
