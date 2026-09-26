import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../shared/models/user_model.dart';
import '../../home/screens/home_shell.dart';

class TaskSelectionScreen extends StatefulWidget {
  final UserModel user;
  const TaskSelectionScreen({super.key, required this.user});

  @override
  State<TaskSelectionScreen> createState() => _TaskSelectionScreenState();
}

class _TaskSelectionScreenState extends State<TaskSelectionScreen> {
  List<Map<String, dynamic>> _availableTasks = [];
  List<Map<String, dynamic>> _selectedTasks = [];
  bool _isLoading = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadTasks();
  }

  Future<void> _loadTasks() async {
    try {
      final response = await ApiService.dio.get('/user-tasks/available-tasks');
      setState(() {
        _availableTasks = List<Map<String, dynamic>>.from(response.data);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  bool _isSelected(String taskId) =>
      _selectedTasks.any((t) => t['task_id'] == taskId);

  int _dailyTaskCount() =>
      _selectedTasks.where((t) => t['frequency'] == 'daily').length;

  void _toggleTask(Map<String, dynamic> task) {
    final taskId = task['id'];
    if (_isSelected(taskId)) {
      // Check minimum
      final sel = _selectedTasks.firstWhere(
          (t) => t['task_id'] == taskId);
      if (sel['frequency'] == 'daily' && _dailyTaskCount() <= 2) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('You need at least 2 daily tasks'),
            backgroundColor: AppColors.error,
          ),
        );
        return;
      }
      setState(() =>
          _selectedTasks.removeWhere((t) => t['task_id'] == taskId));
    } else {
      _showAddTaskDialog(task);
    }
  }

  void _showAddTaskDialog(Map<String, dynamic> task) {
    int pages = 1;
    String frequency = 'daily';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Container(
          padding: EdgeInsets.fromLTRB(
              24, 24, 24,
              MediaQuery.of(context).viewInsets.bottom + 24),
          decoration: const BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(task['title'],
                  style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 24),

              // Pages per day
              const Text('Pages per day',
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 8),
              Row(children: [
                GestureDetector(
                  onTap: () {
                    if (pages > 1) setModalState(() => pages--);
                  },
                  child: Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: const Icon(Icons.remove, color: AppColors.textPrimary),
                  ),
                ),
                Expanded(
                  child: Center(
                    child: Text('$pages',
                        style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: AppColors.primary)),
                  ),
                ),
                GestureDetector(
                  onTap: () => setModalState(() => pages++),
                  child: Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: const Icon(Icons.add, color: AppColors.textPrimary),
                  ),
                ),
              ]),
              const SizedBox(height: 20),

              // Frequency
              const Text('Frequency',
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 8),
              Row(children: ['daily', 'weekly', 'monthly'].map((f) {
                final isSelected = frequency == f;
                return Expanded(
                  child: GestureDetector(
                    onTap: () => setModalState(() => frequency = f),
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppColors.primary
                            : AppColors.background,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: isSelected
                              ? AppColors.primary
                              : AppColors.border,
                        ),
                      ),
                      child: Text(
                        f[0].toUpperCase() + f.substring(1),
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: isSelected
                              ? Colors.white
                              : AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                );
              }).toList()),
              const SizedBox(height: 24),

              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: () {
                    setState(() {
                      _selectedTasks.add({
                        'task_id': task['id'],
                        'title': task['title'],
                        'pages_per_day': pages,
                        'frequency': frequency,
                      });
                    });
                    Navigator.pop(context);
                  },
                  child: const Text('Add Task'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool get _canProceed => _dailyTaskCount() >= 2;

  Future<void> _saveAndContinue() async {
    if (!_canProceed) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please add at least 2 daily tasks'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      for (final task in _selectedTasks) {
        await ApiService.dio.post('/user-tasks/my-tasks', data: {
          'task_id': task['task_id'],
          'pages_per_day': task['pages_per_day'],
          'frequency': task['frequency'],
        });
      }

      if (mounted) {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
              builder: (_) => HomeShell(user: widget.user)),
          (route) => false,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error saving tasks: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
    setState(() => _isSaving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        title: const Text('Choose Your Tasks',
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary)),
        automaticallyImplyLeading: false,
      ),
      body: Column(
        children: [
          // Info banner
          Container(
            margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.accent.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: AppColors.accent.withOpacity(0.3)),
            ),
            child: Row(children: [
              const Icon(Icons.info_outline,
                  color: AppColors.accent, size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Select at least 2 daily tasks. You can add more or modify them later.',
                  style: TextStyle(
                      fontSize: 12, color: AppColors.accent),
                ),
              ),
            ]),
          ),

          // Daily task counter
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Row(children: [
              Text(
                'Daily tasks selected: ${_dailyTaskCount()}',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: _dailyTaskCount() >= 2
                      ? AppColors.primary
                      : AppColors.error,
                ),
              ),
              const Spacer(),
              Text('${_selectedTasks.length} total',
                  style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary)),
            ]),
          ),

          // Task list
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                        color: AppColors.primary))
                : _availableTasks.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.task_outlined,
                                size: 48, color: AppColors.textHint),
                            const SizedBox(height: 12),
                            const Text('No tasks available yet',
                                style: TextStyle(
                                    color: AppColors.textHint)),
                            const SizedBox(height: 8),
                            const Text(
                              'Admin needs to create MyRise tasks first',
                              style: TextStyle(
                                  fontSize: 13,
                                  color: AppColors.textHint),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _availableTasks.length,
                        itemBuilder: (context, i) {
                          final task = _availableTasks[i];
                          final selected = _isSelected(task['id']);
                          final selTask = selected
                              ? _selectedTasks.firstWhere(
                                  (t) => t['task_id'] == task['id'])
                              : null;

                          return GestureDetector(
                            onTap: () => _toggleTask(task),
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: selected
                                    ? AppColors.primary.withOpacity(0.05)
                                    : AppColors.surface,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(
                                  color: selected
                                      ? AppColors.primary.withOpacity(0.4)
                                      : AppColors.border,
                                  width: selected ? 1.5 : 1,
                                ),
                              ),
                              child: Row(children: [
                                // Checkbox
                                AnimatedContainer(
                                  duration:
                                      const Duration(milliseconds: 200),
                                  width: 26, height: 26,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: selected
                                        ? AppColors.primary
                                        : Colors.transparent,
                                    border: Border.all(
                                      color: selected
                                          ? AppColors.primary
                                          : AppColors.border,
                                      width: 2,
                                    ),
                                  ),
                                  child: selected
                                      ? const Icon(Icons.check,
                                          color: Colors.white, size: 16)
                                      : null,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(task['title'],
                                          style: TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.w600,
                                              color: selected
                                                  ? AppColors.primary
                                                  : AppColors.textPrimary)),
                                      if (selected && selTask != null)
                                        Text(
                                          '${selTask['pages_per_day']} pages · ${selTask['frequency']}',
                                          style: const TextStyle(
                                              fontSize: 12,
                                              color: AppColors.textSecondary),
                                        ),
                                    ],
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.accentLight,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text('+${task['points']} pts',
                                      style: const TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w600,
                                          color: AppColors.accent)),
                                ),
                              ]),
                            ),
                          );
                        },
                      ),
          ),

          // Bottom button
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            child: Column(children: [
              if (!_canProceed)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    'Add ${2 - _dailyTaskCount()} more daily task(s) to continue',
                    style: const TextStyle(
                        fontSize: 13, color: AppColors.error),
                    textAlign: TextAlign.center,
                  ),
                ),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _canProceed && !_isSaving
                      ? _saveAndContinue
                      : null,
                  child: _isSaving
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2))
                      : const Text('Start My Journey'),
                ),
              ),
            ]),
          ),
        ],
      ),
    );
  }
}
