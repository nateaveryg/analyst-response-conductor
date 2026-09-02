import 'package:flutter/material.dart';
import '../models/workspace.dart';

class WorkspaceHeader extends StatelessWidget {
  final List<Workspace> workspaces;
  final Workspace? selectedWorkspace;
  final Function(Workspace) onWorkspaceSelected;
  final VoidCallback onNewWorkspace;
  final VoidCallback onOpenRadar;
  final VoidCallback onOpenArtifacts;

  const WorkspaceHeader({
    Key? key,
    required this.workspaces,
    required this.selectedWorkspace,
    required this.onWorkspaceSelected,
    required this.onNewWorkspace,
    required this.onOpenRadar,
    required this.onOpenArtifacts,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final bool isReadOnly = selectedWorkspace != null && !selectedWorkspace!.canEdit;

    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        border: Border(
          bottom: BorderSide(color: Color(0xFF334155)),
        ),
      ),
      child: Row(
        children: [
          // Platform Brand & Logo
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF1A73E8).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.hub_outlined, color: Color(0xFF8AB4F8), size: 20),
              ),
              const SizedBox(width: 10),
              const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'The Conductor v3',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.3,
                    ),
                  ),
                  Text(
                    'Analyst Response Agent • Go & Flutter Engine',
                    style: TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(width: 24),

          // Workspace Dropdown Switcher
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: selectedWorkspace?.id,
                dropdownColor: const Color(0xFF0F172A),
                icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF94A3B8)),
                style: const TextStyle(color: Colors.white, fontSize: 13),
                hint: const Text('Select Workspace', style: TextStyle(color: Color(0xFF94A3B8))),
                items: workspaces.map((w) {
                  return DropdownMenuItem<String>(
                    value: w.id,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          w.canEdit ? Icons.folder_open : Icons.lock_outline,
                          size: 16,
                          color: w.canEdit ? const Color(0xFF8AB4F8) : const Color(0xFFF2994A),
                        ),
                        const SizedBox(width: 8),
                        Text(w.name),
                        if (!w.canEdit) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF2994A).withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text('Read-Only', style: TextStyle(color: Color(0xFFF2994A), fontSize: 9)),
                          ),
                        ],
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (id) {
                  if (id != null) {
                    final ws = workspaces.firstWhere((w) => w.id == id);
                    onWorkspaceSelected(ws);
                  }
                },
              ),
            ),
          ),
          const SizedBox(width: 8),

          // New Workspace Button
          IconButton(
            tooltip: 'Create New Workspace',
            icon: const Icon(Icons.add_circle_outline, color: Color(0xFF8AB4F8), size: 20),
            onPressed: onNewWorkspace,
          ),

          if (isReadOnly) ...[
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF7C2D12).withOpacity(0.6),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFF97316)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.shield_outlined, color: Color(0xFFFB923C), size: 14),
                  SizedBox(width: 6),
                  Text(
                    'Enterprise Read-Only Mode (Owner: AR Leads)',
                    style: TextStyle(color: Color(0xFFFED7AA), fontSize: 11, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
          ],

          const Spacer(),

          // Quick Action Header Buttons
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF8AB4F8),
              side: const BorderSide(color: Color(0xFF334155)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            icon: const Icon(Icons.radar, size: 16),
            label: const Text('Governance Radar', style: TextStyle(fontSize: 12)),
            onPressed: onOpenRadar,
          ),
          const SizedBox(width: 8),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFFCBD5E1),
              side: const BorderSide(color: Color(0xFF334155)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            icon: const Icon(Icons.save_outlined, size: 16),
            label: const Text('Saved Artifacts', style: TextStyle(fontSize: 12)),
            onPressed: onOpenArtifacts,
          ),
        ],
      ),
    );
  }
}
