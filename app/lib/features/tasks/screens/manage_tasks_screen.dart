import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class ManageTasksScreen extends StatefulWidget {
  const ManageTasksScreen({super.key});

  @override
  State<ManageTasksScreen> createState() => _ManageTasksScreenState();
}

class _ManageTasksScreenState extends State<ManageTasksScreen> {
  List<Map<String, dynamic>> _myTasks = [];
  List<Map<String, dynamic>> _availableTasks = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() => _isLoading = true);
    try {
      final myRes = await ApiService.dio.get('/user-tasks/my-tasks');
      final avRes = await ApiService.dio.get('/user-tasks/available-tasks');
      setState(() {
        _myTasks = List<Map<String, dynamic>>.from(myRes.data);
        _availableTasks = List<Map<String, dynamic>>.from(avRes.data);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  int _dailyTaskCount() =>
      _myTasks.where((t) => t['frequency'] == 'daily').length;

  void _showUpdateDialog(Map<String, dynamic> task) {
    int pages = task['pages_per_day'] ?? 1;
    String frequency = task['frequency'] ?? 'daily';

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
              const SizedBox(height: 4),
              const Text(
                'You can change pages and frequency only',
                style: TextStyle(
                    fontSize: 12, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 24),

              // Pages
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
                    child: const Icon(Icons.remove),
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
                    child: const Icon(Icons.add),
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
                final isSel = frequency == f;
                return Expanded(
                  child: GestureDetector(
                    onTap: () => setModalState(() => frequency = f),
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: isSel ? AppColors.primary : AppColors.background,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: isSel ? AppColors.primary : AppColors.border,
                        ),
                      ),
                      child: Text(
                        f[0].toUpperCase() + f.substring(1),
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                            color: isSel ? Colors.white : AppColors.textSecondary),
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
                  onPressed: () async {
                    Navigator.pop(context);
                    try {
                      await ApiService.dio.put(
                          '/user-tasks/my-tasks/${task['id']}',
                          data: {
                            'pages_per_day': pages,
                            'frequency': frequency,
                          });
                      await _loadAll();
                    } catch (e) {
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(e.toString()),
                            backgroundColor: AppColors.error,
                          ),
                        );
                      }
                    }
                  },
                  child: const Text('Update Task'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAddTaskDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        String? selectedTaskId;
        int pages = 1;
        String frequency = 'daily';

        final unselected = _availableTasks
            .where((t) =>
                !_myTasks.any((mt) => mt['task_id'] == t['id']))
            .toList();

        if (unselected.isEmpty) {
          return Container(
            padding: const EdgeInsets.all(24),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              borderRadius:
                  BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.check_circle_outline,
                  color: AppColors.primary, size: 48),
              const SizedBox(height: 16),
              const Text('All available tasks added!',
                  style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 8),
              const Text(
                  'You have added all tasks from the MyRise pool.',
                  style: TextStyle(color: AppColors.textSecondary),
                  textAlign: TextAlign.center),
            ]),
          );
        }

        selectedTaskId = unselected.first['id'];

        return StatefulBuilder(
          builder: (context, setModalState) => Container(
            padding: EdgeInsets.fromLTRB(
                24, 24, 24,
                MediaQuery.of(context).viewInsets.bottom + 24),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              borderRadius:
                  BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Add Task',
                    style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 20),

                // Task selector
                const Text('Task',
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: selectedTaskId,
                  decoration: const InputDecoration(),
                  items: unselected
                      .map((t) => DropdownMenuItem(
                            value: t['id'] as String,
                            child: Text(t['title']),
                          ))
                      .toList(),
                  onChanged: (v) =>
                      setModalState(() => selectedTaskId = v),
                ),
                const SizedBox(height: 16),

                // Pages
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
                      child: const Icon(Icons.remove),
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
                      child: const Icon(Icons.add),
                    ),
                  ),
                ]),
                const SizedBox(height: 16),

                // Frequency
                const Text('Frequency',
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                Row(children: ['daily', 'weekly', 'monthly'].map((f) {
                  final isSel = frequency == f;
                  return Expanded(
                    child: GestureDetector(
                      onTap: () => setModalState(() => frequency = f),
                      child: Container(
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: isSel
                              ? AppColors.primary
                              : AppColors.background,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: isSel
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
                              color: isSel
                                  ? Colors.white
                                  : AppColors.textSecondary),
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
                    onPressed: () async {
                      Navigator.pop(context);
                      try {
                        await ApiService.dio.post(
                            '/user-tasks/my-tasks',
                            data: {
                              'task_id': selectedTaskId,
                              'pages_per_day': pages,
                              'frequency': frequency,
                            });
                        await _loadAll();
                      } catch (e) {
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(e.toString()),
                              backgroundColor: AppColors.error,
                            ),
                          );
                        }
                      }
                    },
                    child: const Text('Add Task'),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _deleteTask(Map<String, dynamic> task) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Task'),
        content: Text('Remove "${task['title']}" from your tasks?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
                foregroundColor: AppColors.error),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ApiService.dio.delete('/user-tasks/my-tasks/${task['id']}');
        await _loadAll();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(e.toString().contains('2 daily')
                  ? 'You need at least 2 daily tasks'
                  : 'Failed to remove task'),
              backgroundColor: AppColors.error,
            ),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        title: const Text('Manage My Tasks',
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new,
              color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.primary))
          : Column(
              children: [
                // Min task info
                Container(
                  margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: _dailyTaskCount() >= 2
                        ? AppColors.primary.withOpacity(0.06)
                        : AppColors.error.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: _dailyTaskCount() >= 2
                          ? AppColors.primary.withOpacity(0.2)
                          : AppColors.error.withOpacity(0.2),
                    ),
                  ),
                  child: Row(children: [
                    Icon(
                      _dailyTaskCount() >= 2
                          ? Icons.check_circle_outline
                          : Icons.warning_amber_outlined,
                      color: _dailyTaskCount() >= 2
                          ? AppColors.primary
                          : AppColors.error,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Daily tasks: ${_dailyTaskCount()} (minimum 2 required)',
                      style: TextStyle(
                          fontSize: 12,
                          color: _dailyTaskCount() >= 2
                              ? AppColors.primary
                              : AppColors.error),
                    ),
                  ]),
                ),

                // Task list
                Expanded(
                  child: _myTasks.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.task_outlined,
                                  size: 48, color: AppColors.textHint),
                              const SizedBox(height: 12),
                              const Text('No tasks yet',
                                  style: TextStyle(
                                      color: AppColors.textHint,
                                      fontSize: 15)),
                              const SizedBox(height: 8),
                              TextButton(
                                onPressed: _showAddTaskDialog,
                                child: const Text('Add your first task'),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _myTasks.length,
                          itemBuilder: (context, i) {
                            final task = _myTasks[i];
                            return Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              decoration: BoxDecoration(
                                color: AppColors.surface,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: AppColors.border),
                              ),
                              child: ListTile(
                                contentPadding:
                                    const EdgeInsets.fromLTRB(16, 8, 8, 8),
                                title: Text(task['title'],
                                    style: const TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textPrimary)),
                                subtitle: Text(
                                  '${task['pages_per_day']} pages/day · ${task['frequency']}',
                                  style: const TextStyle(
                                      fontSize: 12,
                                      color: AppColors.textSecondary),
                                ),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    // Update button
                                    TextButton(
                                      onPressed: () =>
                                          _showUpdateDialog(task),
                                      style: TextButton.styleFrom(
                                        foregroundColor: AppColors.primary,
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 10),
                                      ),
                                      child: const Text('Update',
                                          style:
                                              TextStyle(fontSize: 13)),
                                    ),
                                    // Delete button
                                    TextButton(
                                      onPressed: () =>
                                          _deleteTask(task),
                                      style: TextButton.styleFrom(
                                        foregroundColor: AppColors.error,
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 10),
                                      ),
                                      child: const Text('Delete',
                                          style: TextStyle(fontSize: 13)),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),

                // Add Task button
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                  child: SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: OutlinedButton.icon(
                      onPressed: _showAddTaskDialog,
                      icon: const Icon(Icons.add),
                      label: const Text('Add Task'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.primary,
                        side: const BorderSide(color: AppColors.primary),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
