import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../shared/models/user_model.dart';
import '../../tasks/task_theme.dart';

class EventsScreen extends StatefulWidget {
  final UserModel user;
  const EventsScreen({super.key, required this.user});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  /// Same six colors as the task list, assigned by position.
  /// Keyed by event id so an event has one color in both lists.
  TaskTheme _eventTheme(Map<String, dynamic> event) {
    final ids = <String>[];
    for (final ev in [..._myEvents, ..._todayEvents]) {
      final id = (ev['id'] ?? ev['name']).toString();
      if (!ids.contains(id)) ids.add(id);
    }
    final idx = ids.indexOf((event['id'] ?? event['name']).toString());
    return TaskTheme.sequence(idx < 0 ? 0 : idx);
  }

  List<dynamic> _todayEvents = [];
  List<dynamic> _myEvents = [];
  Map<String, dynamic>? _ramadanBanner;
  Map<String, dynamic>? _taraweehMotivation;
  bool _isLoading = true;
  bool _canAddWeekly = true;
  bool _canAddMonthly = true;
  int _weeklyCount = 0;
  int _monthlyCount = 0;
  Map<String, dynamic> _limits = {"weekly": 3, "monthly": 1};

  @override
  void initState() {
    super.initState();
    _loadEvents();
  }

  Future<void> _loadEvents() async {
    setState(() => _isLoading = true);
    try {
      final todayRes = await ApiService.dio.get('/events/today');
      final myRes = await ApiService.dio.get('/events/my-events');
      try {
        final motRes = await ApiService.dio.get(
            '/settings/taraweeh-motivation');
        setState(() => _taraweehMotivation = motRes.data);
      } catch (_) {}
      setState(() {
        _todayEvents = todayRes.data['today'] ?? [];
        _ramadanBanner = todayRes.data['ramadan_banner'];
        _myEvents = myRes.data['events'] ?? [];
        _canAddWeekly = myRes.data['can_add_weekly'] ?? true;
        _canAddMonthly = myRes.data['can_add_monthly'] ?? true;
        _weeklyCount = myRes.data['weekly_count'] ?? 0;
        _monthlyCount = myRes.data['monthly_count'] ?? 0;
        _limits = myRes.data['limits'] ?? {"weekly": 3, "monthly": 1};
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _toggleEvent(Map<String, dynamic> event) async {
    try {
      await ApiService.dio.post('/events/complete/${event['id']}');
      await _loadEvents();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(event['is_completed']
              ? 'Event unchecked'
              : '${event['name']} completed! +${event['points']} pts'),
          backgroundColor: event['is_completed']
              ? AppColors.textSecondary
              : AppColors.primary,
          behavior: SnackBarBehavior.floating,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Failed: $e'),
          backgroundColor: AppColors.error,
          behavior: SnackBarBehavior.floating,
        ));
      }
    }
  }

  void _showAddEventDialog() {
    final nameController = TextEditingController();
    final descController = TextEditingController();
    String eventType = 'weekly';
    int dayOfWeek = 0;
    int? dayOfMonth;
    int? weekOfMonth;
    String monthlyPattern = 'specific_day';
    String startTime = '09:00';
    TimeOfDay selectedTime = const TimeOfDay(hour: 9, minute: 0);
    final days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
    final weeks = ['First','Second','Third','Fourth'];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Container(
          height: MediaQuery.of(context).size.height * 0.85,
          padding: EdgeInsets.fromLTRB(24, 24, 24,
              MediaQuery.of(context).viewInsets.bottom + 24),
          decoration: const BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Add Event',
                        style: TextStyle(fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: AppColors.textPrimary)),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                const Text('Event Name *',
                    style: TextStyle(fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(
                      hintText: 'e.g. Quran Study Circle'),
                ),
                const SizedBox(height: 16),
                const Text('Description (optional)',
                    style: TextStyle(fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                TextField(
                  controller: descController,
                  decoration: const InputDecoration(
                      hintText: 'Brief description...'),
                  maxLines: 2,
                ),
                const SizedBox(height: 16),
                const Text('Frequency',
                    style: TextStyle(fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: _canAddWeekly
                          ? () => setModalState(() => eventType = 'weekly')
                          : null,
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: eventType == 'weekly'
                              ? AppColors.primary : AppColors.background,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: eventType == 'weekly'
                                ? AppColors.primary : AppColors.border,
                          ),
                        ),
                        child: Column(children: [
                          Text('Weekly', textAlign: TextAlign.center,
                              style: TextStyle(fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: eventType == 'weekly'
                                      ? Colors.white
                                      : _canAddWeekly
                                          ? AppColors.textPrimary
                                          : AppColors.textHint)),
                          Text('$_weeklyCount/${_limits['weekly']}',
                              style: TextStyle(fontSize: 11,
                                  color: eventType == 'weekly'
                                      ? Colors.white70
                                      : AppColors.textHint)),
                        ]),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: GestureDetector(
                      onTap: _canAddMonthly
                          ? () => setModalState(() => eventType = 'monthly')
                          : null,
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: eventType == 'monthly'
                              ? AppColors.primary : AppColors.background,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: eventType == 'monthly'
                                ? AppColors.primary : AppColors.border,
                          ),
                        ),
                        child: Column(children: [
                          Text('Monthly', textAlign: TextAlign.center,
                              style: TextStyle(fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: eventType == 'monthly'
                                      ? Colors.white
                                      : _canAddMonthly
                                          ? AppColors.textPrimary
                                          : AppColors.textHint)),
                          Text('$_monthlyCount/${_limits['monthly']}',
                              style: TextStyle(fontSize: 11,
                                  color: eventType == 'monthly'
                                      ? Colors.white70
                                      : AppColors.textHint)),
                        ]),
                      ),
                    ),
                  ),
                ]),
                const SizedBox(height: 16),

                if (eventType == 'weekly') ...[
                  const Text('Day of Week',
                      style: TextStyle(fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: AppColors.textPrimary)),
                  const SizedBox(height: 8),
                  Wrap(spacing: 8, runSpacing: 8,
                    children: List.generate(7, (i) {
                      final isSelected = dayOfWeek == i;
                      return GestureDetector(
                        onTap: () => setModalState(() => dayOfWeek = i),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? AppColors.primary : AppColors.background,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isSelected
                                  ? AppColors.primary : AppColors.border,
                            ),
                          ),
                          child: Text(days[i].substring(0, 3),
                              style: TextStyle(fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                  color: isSelected
                                      ? Colors.white
                                      : AppColors.textPrimary)),
                        ),
                      );
                    }),
                  ),
                ],

                if (eventType == 'monthly') ...[
                  const Text('Schedule Type',
                      style: TextStyle(fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: AppColors.textPrimary)),
                  const SizedBox(height: 8),
                  ...['specific_day','weekly_day','nth_weekday'].map((p) {
                    final labels = {
                      'specific_day': 'Specific day (e.g. 24th)',
                      'weekly_day': 'Every weekday (e.g. every Monday)',
                      'nth_weekday': 'Nth weekday (e.g. first Monday)',
                    };
                    return RadioListTile<String>(
                      value: p,
                      groupValue: monthlyPattern,
                      title: Text(labels[p]!,
                          style: const TextStyle(fontSize: 13)),
                      onChanged: (v) =>
                          setModalState(() => monthlyPattern = v!),
                      activeColor: AppColors.primary,
                      contentPadding: EdgeInsets.zero,
                    );
                  }),
                  const SizedBox(height: 8),
                  if (monthlyPattern == 'specific_day') ...[
                    const Text('Day of Month',
                        style: TextStyle(fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 8),
                    TextField(
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(hintText: '1-31'),
                      onChanged: (v) => setModalState(
                          () => dayOfMonth = int.tryParse(v)),
                    ),
                  ],
                  if (monthlyPattern == 'weekly_day' ||
                      monthlyPattern == 'nth_weekday') ...[
                    if (monthlyPattern == 'nth_weekday') ...[
                      const Text('Which week?',
                          style: TextStyle(fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: AppColors.textPrimary)),
                      const SizedBox(height: 8),
                      Wrap(spacing: 8,
                        children: List.generate(4, (i) {
                          final isSelected = weekOfMonth == i + 1;
                          return GestureDetector(
                            onTap: () =>
                                setModalState(() => weekOfMonth = i + 1),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? AppColors.primary
                                    : AppColors.background,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: isSelected
                                      ? AppColors.primary : AppColors.border,
                                ),
                              ),
                              child: Text(weeks[i],
                                  style: TextStyle(fontSize: 12,
                                      color: isSelected
                                          ? Colors.white
                                          : AppColors.textPrimary)),
                            ),
                          );
                        }),
                      ),
                      const SizedBox(height: 12),
                    ],
                    const Text('Day of Week',
                        style: TextStyle(fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8,
                      children: List.generate(7, (i) {
                        final isSelected = dayOfWeek == i;
                        return GestureDetector(
                          onTap: () => setModalState(() => dayOfWeek = i),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? AppColors.primary : AppColors.background,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: isSelected
                                    ? AppColors.primary : AppColors.border,
                              ),
                            ),
                            child: Text(days[i].substring(0, 3),
                                style: TextStyle(fontSize: 12,
                                    color: isSelected
                                        ? Colors.white
                                        : AppColors.textPrimary)),
                          ),
                        );
                      }),
                    ),
                  ],
                ],

                const SizedBox(height: 16),
                const Text('Start Time',
                    style: TextStyle(fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                GestureDetector(
                  onTap: () async {
                    final picked = await showTimePicker(
                      context: context,
                      initialTime: selectedTime,
                    );
                    if (picked != null) {
                      setModalState(() {
                        selectedTime = picked;
                        startTime =
                            '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
                      });
                    }
                  },
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(children: [
                      const Icon(Icons.access_time,
                          color: AppColors.primary, size: 20),
                      const SizedBox(width: 10),
                      Text(selectedTime.format(context),
                          style: const TextStyle(fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: AppColors.textPrimary)),
                    ]),
                  ),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: () async {
                      if (nameController.text.trim().isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text('Please enter event name')));
                        return;
                      }
                      try {
                        await ApiService.dio.post('/events/my-events',
                            data: {
                              'name': nameController.text.trim(),
                              'description':
                                  descController.text.trim().isEmpty
                                      ? null
                                      : descController.text.trim(),
                              'event_type': eventType,
                              'day_of_week': dayOfWeek,
                              'day_of_month': monthlyPattern ==
                                      'specific_day'
                                  ? dayOfMonth
                                  : null,
                              'week_of_month': monthlyPattern ==
                                      'nth_weekday'
                                  ? weekOfMonth
                                  : null,
                              'monthly_pattern': eventType == 'monthly'
                                  ? monthlyPattern
                                  : null,
                              'start_time': startTime,
                            });
                        Navigator.pop(context);
                        await _loadEvents();
                        if (mounted) {
                          ScaffoldMessenger.of(context)
                              .showSnackBar(SnackBar(
                            content: Text(
                                '${nameController.text} added!'),
                            backgroundColor: AppColors.primary,
                            behavior: SnackBarBehavior.floating,
                          ));
                        }
                      } catch (e) {
                        if (mounted) {
                          ScaffoldMessenger.of(context)
                              .showSnackBar(SnackBar(
                            content: Text(e.toString()),
                            backgroundColor: AppColors.error,
                            behavior: SnackBarBehavior.floating,
                          ));
                        }
                      }
                    },
                    child: const Text('Add Event'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _deleteEvent(Map<String, dynamic> event) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Event'),
        content: Text('Remove "${event['name']}"?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              style: TextButton.styleFrom(
                  foregroundColor: AppColors.error),
              child: const Text('Remove')),
        ],
      ),
    );
    if (confirmed == true) {
      await ApiService.dio.delete('/events/my-events/${event['id']}');
      await _loadEvents();
    }
  }

  String _getFormattedDate() {
    final now = DateTime.now();
    const months = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec'];
    const days = ['Monday','Tuesday','Wednesday','Thursday',
                  'Friday','Saturday','Sunday'];
    return '${days[now.weekday - 1]}, ${months[now.month - 1]} ${now.day}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        automaticallyImplyLeading: false,
        toolbarHeight: 72,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Events',
                style: TextStyle(fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary)),
            Text(_getFormattedDate(),
                style: const TextStyle(fontSize: 13,
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.normal)),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: TextButton.icon(
              onPressed: _showAddEventDialog,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Add'),
              style: TextButton.styleFrom(
                  foregroundColor: AppColors.primary),
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(
              color: AppColors.primary))
          : RefreshIndicator(
              onRefresh: _loadEvents,
              color: AppColors.primary,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Ramadan banner — only shown 30 days before or during Ramadan
                    if (_ramadanBanner != null) ...[
                      Container(
                        margin: const EdgeInsets.only(bottom: 16),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: _ramadanBanner!['type'] == 'ramadan_here'
                                ? [const Color(0xFF1D6E56), const Color(0xFF0F4A3A)]
                                : [const Color(0xFF1D2B55), const Color(0xFF2D3B7A)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Row(children: [
                          Text(
                            _ramadanBanner!['type'] == 'ramadan_here' ? '🌙' : '📅',
                            style: const TextStyle(fontSize: 28),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _ramadanBanner!['title'] ?? '',
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.white,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  _ramadanBanner!['phrase'] ?? '',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: Colors.white70,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ]),
                      ),
                    ],

                    if (_todayEvents.isNotEmpty) ...[
                      const Text("Today's Events",
                          style: TextStyle(fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary)),
                      const SizedBox(height: 10),
                      ..._todayEvents.map((e) => _EventCard(
                            event: e,
                            theme: _eventTheme(e),
                            onToggle: () => _toggleEvent(e),
                            showCheckbox: true,
                          )),
                      const SizedBox(height: 24),
                    ],
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('My Events',
                            style: TextStyle(fontSize: 15,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary)),
                        Text(
                          'Weekly: $_weeklyCount/${_limits['weekly']}  '
                          'Monthly: $_monthlyCount/${_limits['monthly']}',
                          style: const TextStyle(fontSize: 11,
                              color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (_myEvents.isEmpty)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(32),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Column(children: [
                          const Icon(Icons.event_outlined,
                              size: 40, color: AppColors.textHint),
                          const SizedBox(height: 12),
                          const Text('No events yet',
                              style: TextStyle(color: AppColors.textHint)),
                          const SizedBox(height: 8),
                          TextButton(
                            onPressed: _showAddEventDialog,
                            child: const Text('Add your first event'),
                          ),
                        ]),
                      )
                    else
                      ..._myEvents.map((e) => _EventCard(
                            event: e,
                            theme: _eventTheme(e),
                            onDelete: () => _deleteEvent(e),
                            showSchedule: true,
                          )),
                  ],
                ),
              ),
            ),
    );
  }
}

class _EventCard extends StatelessWidget {
  final Map<String, dynamic> event;
  final VoidCallback? onToggle;
  final VoidCallback? onDelete;
  final bool showCheckbox;
  final bool showSchedule;
  final TaskTheme? theme;

  const _EventCard({
    required this.event,
    this.theme,
    this.onToggle,
    this.onDelete,
    this.showCheckbox = false,
    this.showSchedule = false,
  });

  @override
  Widget build(BuildContext context) {
    final isFixed = event['is_fixed'] ?? false;
    final isCompleted = event['is_completed'] ?? false;
    final isTaraweeh = event['is_taraweeh'] ?? false;
    final taraweehCount = event['taraweeh_count'] ?? 0;
    final taraweehPhrase = event['taraweeh_phrase'] ?? '';

    return Column(
      children: [
        // Taraweeh count banner
        if (isTaraweeh) Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1D2B55), Color(0xFF2D3B7A)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(children: [
            const Text('🌙', style: TextStyle(fontSize: 24)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Taraweeh attended: $taraweehCount nights',
                    style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Colors.white),
                  ),
                  if (taraweehPhrase.isNotEmpty)
                    Text(taraweehPhrase,
                        style: const TextStyle(
                            fontSize: 12, color: Colors.white70)),
                ],
              ),
            ),
          ]),
        ),
    Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: theme?.tint ??
            (isCompleted
                ? AppColors.primary.withOpacity(0.04)
                : AppColors.surface),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isCompleted
              ? AppColors.primary.withOpacity(0.3)
              : theme != null
                  ? theme!.accent.withOpacity(0.45)
                  : isFixed
                      ? AppColors.accent.withOpacity(0.4)
                      : AppColors.border,
          width: theme != null ? 1.2 : 1,
        ),
      ),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          width: 44, height: 44,
          decoration: BoxDecoration(
            color: theme != null
                ? theme!.accent.withOpacity(0.14)
                : isFixed
                    ? AppColors.accent.withOpacity(0.1)
                    : AppColors.primary.withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            event['fixed_type'] == 'jummah'
                ? Icons.mosque_rounded
                : (event['fixed_type']?.toString().contains('eid') == true)
                    ? Icons.star_rounded
                    : Icons.event_rounded,
            color: theme?.accent ??
                (isFixed ? AppColors.accent : AppColors.primary),
            size: 22,
          ),
        ),
        title: Text(event['name'],
            style: TextStyle(fontSize: 14,
                fontWeight: FontWeight.w600,
                color: isCompleted
                    ? AppColors.primary
                    : AppColors.textPrimary)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (event['description'] != null)
              Text(event['description'],
                  style: const TextStyle(
                      fontSize: 12, color: AppColors.textSecondary)),
            if (showSchedule && event['schedule'] != null)
              Text(event['schedule'],
                  style: const TextStyle(
                      fontSize: 12, color: AppColors.textSecondary)),
            if (showSchedule && event['next_occurrence'] != null)
              Text('Next: ${event['next_occurrence']}',
                  style: const TextStyle(
                      fontSize: 11, color: AppColors.primary)),
          ],
        ),
        trailing: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.accentLight,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text('+${event['points']} pts',
                style: const TextStyle(fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.accent)),
          ),
          if (showCheckbox && onToggle != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onToggle,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 28, height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isCompleted
                      ? AppColors.primary : Colors.transparent,
                  border: Border.all(
                    color: isCompleted
                        ? AppColors.primary
                        : theme?.accent.withOpacity(0.6) ?? AppColors.border,
                    width: 2,
                  ),
                ),
                child: isCompleted
                    ? const Icon(Icons.check,
                        color: Colors.white, size: 16)
                    : null,
              ),
            ),
          ],
          if (onDelete != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onDelete,
              child: const Icon(Icons.delete_outline,
                  color: AppColors.error, size: 20),
            ),
          ],
        ]),
      ),
    ),
    ], // end Column
    );
  }
}
