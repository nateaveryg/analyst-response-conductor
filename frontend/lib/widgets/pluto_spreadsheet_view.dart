import 'package:flutter/material.dart';
import 'package:pluto_grid/pluto_grid.dart';
import '../models/rfi_questionnaire.dart';

class PlutoSpreadsheetView extends StatefulWidget {
  final List<RfiQuestionRow> questions;
  final Function(RfiQuestionRow updatedRow)? onRowUpdated;
  final bool isReadOnly;

  const PlutoSpreadsheetView({
    Key? key,
    required this.questions,
    this.onRowUpdated,
    this.isReadOnly = false,
  }) : super(key: key);

  @override
  State<PlutoSpreadsheetView> createState() => _PlutoSpreadsheetViewState();
}

class _PlutoSpreadsheetViewState extends State<PlutoSpreadsheetView> {
  late final List<PlutoColumn> columns;
  late final List<PlutoRow> rows;
  String selectedTab = 'All Tabs';

  @override
  void initState() {
    super.initState();
    _buildColumns();
    _buildRows();
  }

  void _buildColumns() {
    columns = [
      PlutoColumn(
        title: 'Section ID',
        field: 'section_id',
        type: PlutoColumnType.text(),
        width: 100,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Worksheet Tab',
        field: 'worksheet_tab',
        type: PlutoColumnType.text(),
        width: 180,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'RFI Question Text',
        field: 'question_text',
        type: PlutoColumnType.text(),
        width: 320,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Assigned SME',
        field: 'assigned_sme',
        type: PlutoColumnType.select([
          'security-sme@google.com',
          'devops-sme@google.com',
          'ai-sme@google.com',
          'data-sme@google.com',
          'gke-sme@google.com',
        ]),
        width: 200,
        readOnly: widget.isReadOnly,
      ),
      PlutoColumn(
        title: 'Confidence',
        field: 'grounding_confidence',
        type: PlutoColumnType.number(format: '#,###.0%'),
        width: 110,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Offered (Built-in)',
        field: 'offered_natively',
        type: PlutoColumnType.select(['Yes (Built-in)', 'Yes (Preview)', 'Partner / Add-on', 'Roadmap']),
        width: 150,
        readOnly: widget.isReadOnly,
      ),
      PlutoColumn(
        title: 'Grounded Draft Response',
        field: 'draft_response',
        type: PlutoColumnType.text(),
        width: 450,
        readOnly: widget.isReadOnly,
      ),
      PlutoColumn(
        title: 'Prior Provenance Source',
        field: 'source_rfi_title',
        type: PlutoColumnType.text(),
        width: 240,
        readOnly: true,
      ),
      PlutoColumn(
        title: 'Review Status',
        field: 'status',
        type: PlutoColumnType.select(['Draft', 'In Review', 'Approved', 'Waiver Pending']),
        width: 130,
        readOnly: widget.isReadOnly,
      ),
    ];
  }

  void _buildRows() {
    rows = widget.questions.map((q) {
      return PlutoRow(cells: {
        'section_id': PlutoCell(value: q.sectionId),
        'worksheet_tab': PlutoCell(value: q.worksheetTab),
        'question_text': PlutoCell(value: q.questionText),
        'assigned_sme': PlutoCell(value: q.assignedSme),
        'grounding_confidence': PlutoCell(value: q.groundingConfidenceScore / 100.0),
        'offered_natively': PlutoCell(value: q.offeredNatively),
        'draft_response': PlutoCell(value: q.draftResponse),
        'source_rfi_title': PlutoCell(value: q.sourceRfiTitle),
        'status': PlutoCell(value: q.status),
      });
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final tabs = ['All Tabs', ...widget.questions.map((q) => q.worksheetTab).toSet().toList()];

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.withOpacity(0.2)),
      ),
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.table_chart_outlined, color: Color(0xFF1A73E8)),
              const SizedBox(width: 8),
              const Text(
                'Virtualized Multi-Tab Questionnaire Grid (PlutoGrid)',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
              const Spacer(),
              Text(
                '${widget.questions.length} Questions across ${tabs.length - 1} Tabs',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: tabs.map((tab) {
                final isSelected = tab == selectedTab;
                return Padding(
                  padding: const EdgeInsets.only(right: 6.0),
                  child: ChoiceChip(
                    label: Text(tab, style: TextStyle(fontSize: 12, color: isSelected ? Colors.white : Colors.black87)),
                    selected: isSelected,
                    selectedColor: const Color(0xFF1A73E8),
                    onSelected: (val) {
                      if (val) setState(() => selectedTab = tab);
                    },
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 480,
            child: PlutoGrid(
              columns: columns,
              rows: rows,
              configuration: const PlutoGridConfiguration(
                style: PlutoGridStyleConfig(
                  gridBorderColor: Color(0xFFE2E8F0),
                  rowHeight: 44,
                  columnHeight: 38,
                  defaultCellPadding: EdgeInsets.symmetric(horizontal: 8),
                ),
              ),
              onChanged: (PlutoGridOnChangedEvent event) {
                // Cell edited
              },
            ),
          ),
        ],
      ),
    );
  }
}
