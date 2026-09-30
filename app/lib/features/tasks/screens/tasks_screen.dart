import 'package:flutter/material.dart';
import '../task_theme.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/tasks_api.dart';
import '../../../core/services/users_api.dart';
import '../../../shared/models/user_model.dart';
import '../../../shared/models/task_model.dart';
import '../../../shared/widgets/pdf_page_viewer.dart';
import '../../../shared/widgets/excel_content_viewer.dart';

class TasksScreen extends StatefulWidget {
  final UserModel user;
  final String initialFrequency;

  const TasksScreen({
    super.key,
    required this.user,
    this.initialFrequency = 'daily',
  });

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<TaskModel> _tasks = [];
  bool _isLoading = true;
  int _totalPoints = 0;
  double _completionRate = 0.0;
  String _achievementLevel = 'Starter';

  @override
  void initState() {
    super.initState();
    // Set initial tab based on notification frequency
    int initialTab = 0;
    if (widget.initialFrequency == 'weekly') initialTab = 1;
    if (widget.initialFrequency == 'monthly') initialTab = 2;
    _tabController = TabController(
        length: 3, vsync: this, initialIndex: initialTab);
    _totalPoints = widget.user.totalPoints;
    _completionRate = widget.user.completionRate;
    _achievementLevel = widget.user.achievementLevel;
    _loadTasks();
  }

  @override
  void didUpdateWidget(TasksScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialFrequency != oldWidget.initialFrequency) {
      int tab = 0;
      if (widget.initialFrequency == 'weekly') tab = 1;
      if (widget.initialFrequency == 'monthly') tab = 2;
      _tabController.animateTo(tab);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadTasks() async {
    setState(() => _isLoading = true);
    try {
      final data = await TasksApi.getTasks();
      setState(() {
        _tasks = data.map((t) => TaskModel(
          id: t['id']?.toString() ?? '',
          title: t['title']?.toString() ?? '',
          description: t['description']?.toString(),
          frequency: _parseFrequency(t['frequency']),
          points: t['points'] ?? 10,
          isCompleted: t['is_completed'] ?? false,
          infoType: _parseInfoType(t['info_type']),
          infoContent: t['info_content']?.toString(),
        )).toList();
        _isLoading = false;
      });
    } catch (e) {
      print('Load tasks error: $e');
      setState(() => _isLoading = false);
    }
  }

  Future<void> _refreshProfile() async {
    try {
      final profile = await UsersApi.getProfile();
      setState(() {
        _totalPoints = profile['total_points'] ?? 0;
        _completionRate =
            (profile['completion_rate'] as num? ?? 0.0).toDouble();
        _achievementLevel =
            profile['achievement_level'] ?? 'Starter';
      });
    } catch (e) {
      print('Profile refresh error: $e');
    }
  }

  TaskFrequency _parseFrequency(String? freq) {
    switch (freq) {
      case 'weekly': return TaskFrequency.weekly;
      case 'monthly': return TaskFrequency.monthly;
      default: return TaskFrequency.daily;
    }
  }

  TaskInfoType _parseInfoType(String? type) {
    switch (type) {
      case 'text': return TaskInfoType.text;
      case 'image': return TaskInfoType.image;
      case 'video': return TaskInfoType.video;
      default: return TaskInfoType.none;
    }
  }

  List<TaskModel> _getTasks(TaskFrequency freq) =>
      _tasks.where((t) => t.frequency == freq).toList();

  Future<void> _toggleTask(TaskModel task) async {
    try {
      await TasksApi.completeTask(task.id);
      setState(() => task.isCompleted = !task.isCompleted);
      await _refreshProfile();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update task')),
        );
      }
    }
  }

  Color _achievementColor(String level) {
    switch (level) {
      case 'Diamond': return AppColors.diamond;
      case 'Sapphire': return AppColors.sapphire;
      case 'Gold': return AppColors.gold;
      case 'Silver': return AppColors.silver;
      case 'Bronze': return AppColors.bronze;
      default: return AppColors.starter;
    }
  }

  String _getLevelDisplay(String level) {
    final uuidPattern = RegExp(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');
    if (uuidPattern.hasMatch(level.toLowerCase())) return 'My Level';
    return level.split(' - ').first;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Container(
              color: AppColors.surface,
              child: TabBar(
                controller: _tabController,
                labelColor: AppColors.primary,
                unselectedLabelColor: AppColors.textSecondary,
                indicatorColor: AppColors.primary,
                indicatorWeight: 2,
                labelStyle: const TextStyle(
                    fontWeight: FontWeight.w600, fontSize: 14),
                tabs: const [
                  Tab(text: 'Daily'),
                  Tab(text: 'Weekly'),
                  Tab(text: 'Monthly'),
                ],
              ),
            ),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                          color: AppColors.primary))
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildTaskList(_getTasks(TaskFrequency.daily)),
                        _buildTaskList(_getTasks(TaskFrequency.weekly)),
                        _buildTaskList(_getTasks(TaskFrequency.monthly)),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final color = _achievementColor(_achievementLevel);
    return Container(
      color: AppColors.surface,
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Assalamu Alaikum,',
                      style: TextStyle(
                          fontSize: 13,
                          color: AppColors.textSecondary)),
                  Text(widget.user.name,
                      style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary)),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: color.withOpacity(0.3)),
                ),
                child: Text(_achievementLevel,
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: color)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              _StatChip(
                  icon: Icons.layers_rounded,
                  label: _getLevelDisplay(widget.user.programLevel),
                  color: AppColors.primary),
              _StatChip(
                  icon: Icons.stars_rounded,
                  label: '$_totalPoints pts',
                  color: AppColors.accent),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTaskList(List<TaskModel> tasks) {
    // Daily: color follows the content (Quran green, Dua orange...).
    // Weekly/Monthly: same six colors in the same order, by list position.
    // Position comes from the admin's display order, so a task keeps its
    // color when it's checked off.
    TaskTheme themeFor(TaskModel t) => t.frequency == TaskFrequency.daily
        ? TaskTheme.forTitle(t.title)
        : TaskTheme.sequence(tasks.indexOf(t));

    final incomplete = tasks.where((t) => !t.isCompleted).toList();
    final completed = tasks.where((t) => t.isCompleted).toList();

    if (tasks.isEmpty && !_isLoading) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(children: [
            const Icon(Icons.task_outlined,
                size: 48, color: AppColors.textHint),
            const SizedBox(height: 12),
            const Text('No tasks for this period',
                style: TextStyle(
                    color: AppColors.textHint, fontSize: 15)),
            const SizedBox(height: 16),
            TextButton.icon(
              onPressed: _loadTasks,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh'),
            ),
          ]),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadTasks,
      color: AppColors.primary,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (incomplete.isNotEmpty) ...[
            _SectionHeader(
                title: 'Still Working On',
                count: incomplete.length,
                color: AppColors.textPrimary),
            const SizedBox(height: 8),
            ...incomplete.map((t) =>
                _TaskCard(
                    task: t,
                    theme: themeFor(t),
                    onToggle: () => _toggleTask(t))),
            const SizedBox(height: 16),
          ],
          if (completed.isNotEmpty) ...[
            _SectionHeader(
                title: 'Completed',
                count: completed.length,
                color: AppColors.primary),
            const SizedBox(height: 8),
            ...completed.map((t) =>
                _TaskCard(
                    task: t,
                    theme: themeFor(t),
                    onToggle: () => _toggleTask(t))),
          ],
        ],
      ),
    );
  }
}

// ── Stat Chip ─────────────────────────────────────────────────────────────────
class _StatChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _StatChip(
      {required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(8)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 4),
        Text(label,
            style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: color)),
      ]),
    );
  }
}

// ── Section Header ────────────────────────────────────────────────────────────
class _SectionHeader extends StatelessWidget {
  final String title;
  final int count;
  final Color color;
  const _SectionHeader(
      {required this.title,
      required this.count,
      required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Text(title,
          style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: color)),
      const SizedBox(width: 8),
      Container(
        padding:
            const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10)),
        child: Text('$count',
            style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color)),
      ),
    ]);
  }
}

// ── Task Card ─────────────────────────────────────────────────────────────────
class _TaskCard extends StatefulWidget {
  final TaskModel task;
  final VoidCallback onToggle;
  final TaskTheme? theme;
  const _TaskCard({required this.task, required this.onToggle, this.theme});

  @override
  State<_TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends State<_TaskCard> {
  bool _expanded = false;

  bool get _hasInfo {
    if (widget.task.infoContent == null) return false;
    if (widget.task.infoContent!.startsWith('pdf:')) return true;
    return widget.task.infoType != TaskInfoType.none;
  }

  @override
  Widget build(BuildContext context) {
    final theme = widget.theme ?? TaskTheme.forTitle(widget.task.title);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: theme.tint,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: widget.task.isCompleted
              ? AppColors.primary.withOpacity(0.3)
              : theme.accent.withOpacity(0.45),
          width: 1.2,
        ),
      ),
      child: Column(
        children: [
          // ── Main row ──────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            child: Row(
              children: [
                // Checkbox
                GestureDetector(
                  onTap: widget.onToggle,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 26,
                    height: 26,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: widget.task.isCompleted
                          ? AppColors.primary
                          : Colors.transparent,
                      border: Border.all(
                        color: widget.task.isCompleted
                            ? AppColors.primary
                            : theme.accent.withOpacity(0.6),
                        width: 2,
                      ),
                    ),
                    child: widget.task.isCompleted
                        ? const Icon(Icons.check,
                            color: Colors.white, size: 16)
                        : null,
                  ),
                ),
                const SizedBox(width: 12),

                // Title
                Expanded(
                  child: Text(
                    widget.task.title,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: widget.task.isCompleted
                          ? AppColors.textHint
                          : AppColors.textPrimary,
                      decoration: widget.task.isCompleted
                          ? TextDecoration.lineThrough
                          : null,
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Points badge
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.accentLight,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text('+${widget.task.points}',
                      style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.accent)),
                ),

                // Expand toggle
                if (_hasInfo) ...[
                  const SizedBox(width: 6),
                  GestureDetector(
                    onTap: () =>
                        setState(() => _expanded = !_expanded),
                    child: Icon(
                      _expanded
                          ? Icons.keyboard_arrow_up_rounded
                          : Icons.keyboard_arrow_down_rounded,
                      color: AppColors.textHint,
                      size: 22,
                    ),
                  ),
                ],
              ],
            ),
          ),

          // ── Expanded content ──────────────────────────────────────
          if (_hasInfo && _expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: _buildInfoContent(),
            ),
        ],
      ),
    );
  }

  Widget _buildInfoContent() {
    final theme = widget.theme ?? TaskTheme.forTitle(widget.task.title);
    final content = widget.task.infoContent ?? '';

    // PDF task
    if (content.startsWith('pdf:')) {
      return PdfPageViewer(
        taskId: widget.task.id,
        taskTitle: widget.task.title,
        accentColor: theme.accent,
        tintColor: theme.tint,
        inkColor: theme.ink,
      );
    }

    // Excel task
    if (content.startsWith('excel:')) {
      return ExcelContentViewer(
        taskId: widget.task.id,
        taskTitle: widget.task.title,
        accentColor: theme.accent,
        tintColor: theme.tint,
        inkColor: theme.ink,
      );
    }

    // Text
    if (widget.task.infoType == TaskInfoType.text) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          content,
          style: const TextStyle(
            fontSize: 13,
            color: AppColors.textSecondary,
            height: 1.5,
          ),
        ),
      );
    }

    // Image
    if (widget.task.infoType == TaskInfoType.image) {
      return Container(
        height: 140,
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.image_rounded,
                size: 40,
                color: AppColors.primary.withOpacity(0.5)),
            const SizedBox(height: 8),
            const Text('Image from admin',
                style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary)),
          ],
        ),
      );
    }

    // Video
    if (widget.task.infoType == TaskInfoType.video) {
      return Container(
        height: 140,
        decoration: BoxDecoration(
          color: Colors.black87,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.play_arrow_rounded,
                  color: Colors.white, size: 32),
            ),
            const SizedBox(height: 8),
            const Text('Video from admin',
                style: TextStyle(
                    fontSize: 12, color: Colors.white70)),
          ],
        ),
      );
    }

    return const SizedBox.shrink();
  }
}
