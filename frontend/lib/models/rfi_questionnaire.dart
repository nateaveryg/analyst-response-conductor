class RfiQuestionRow {
  final String sectionId;
  final String worksheetTab;
  final String questionText;
  final String assignedSme;
  final String sourceRfiTitle;
  final double groundingConfidenceScore;
  final String draftResponse;
  final String offeredNatively;
  final String status; // Draft, In Review, Approved

  RfiQuestionRow({
    required this.sectionId,
    required this.worksheetTab,
    required this.questionText,
    required this.assignedSme,
    required this.sourceRfiTitle,
    required this.groundingConfidenceScore,
    required this.draftResponse,
    required this.offeredNatively,
    this.status = 'Draft',
  });

  factory RfiQuestionRow.fromJson(Map<String, dynamic> json) => RfiQuestionRow(
    sectionId: json['section_id'] ?? '',
    worksheetTab: json['worksheet_tab'] ?? 'General',
    questionText: json['question_text'] ?? '',
    assignedSme: json['assigned_sme'] ?? 'analyst-sme@google.com',
    sourceRfiTitle: json['source_rfi_title'] ?? '',
    groundingConfidenceScore: (json['grounding_confidence_score'] as num?)?.toDouble() ?? 95.0,
    draftResponse: json['draft_response'] ?? '',
    offeredNatively: json['offered_natively'] ?? 'Yes (Built-in)',
    status: json['status'] ?? 'Draft',
  );

  Map<String, dynamic> toJson() => {
    'section_id': sectionId,
    'worksheet_tab': worksheetTab,
    'question_text': questionText,
    'assigned_sme': assignedSme,
    'source_rfi_title': sourceRfiTitle,
    'grounding_confidence_score': groundingConfidenceScore,
    'draft_response': draftResponse,
    'offered_natively': offeredNatively,
    'status': status,
  };
}
