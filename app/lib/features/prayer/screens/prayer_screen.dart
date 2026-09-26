import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/prayer_time_service.dart';
import '../../../core/services/prayers_api.dart';
import '../../../shared/models/user_model.dart';
import '../../../shared/models/prayer_model.dart';

class PrayerScreen extends StatefulWidget {
  final UserModel user;
  const PrayerScreen({super.key, required this.user});

  @override
  State<PrayerScreen> createState() => _PrayerScreenState();
}

class _PrayerScreenState extends State<PrayerScreen> {
  List<PrayerModel> _prayers = [];
  List<Map<String, dynamic>> _rawPrayerData = [];
  bool _isLoading = true;
  int _totalCompleted = 0;
  int _totalPoints = 0;
  int _levelOrder = 0;

  @override
  void initState() {
    super.initState();
    _loadPrayers();
  }

  Future<void> _loadPrayers() async {
    setState(() => _isLoading = true);
    try {
      final data = await PrayersApi.getTodayPrayers();
      final List<dynamic> prayerList = data['prayers'] ?? [];
      setState(() {
        _totalCompleted = data['total_completed'] ?? 0;
        _totalPoints = data['total_points_earned'] ?? 0;
        _levelOrder = data['level_order'] ?? 0;
        _prayers = prayerList.map((p) => PrayerModel.fromJson(p)).toList();
        _isLoading = false;
      });
    } catch (e) {
      print('Load prayers error: $e');
      setState(() => _isLoading = false);
    }
  }

  Future<void> _togglePrayer(PrayerModel prayer) async {
    if (prayer.isLocked && !prayer.isCompleted) {
      _showSnack(prayer.evradRequired && !prayer.evradCompleted
          ? 'Complete Evrad-u Ezkar / Zikr for ${prayer.displayName} first'
          : prayer.windowExpired
              ? 'The 45-minute window has passed'
              : 'This prayer is locked', isError: true);
      return;
    }
    try {
      await PrayersApi.completePrayer(prayer.name);
      await _loadPrayers();
    } catch (e) {
      _showSnack(e.toString().contains('Evrad')
          ? 'Complete Evrad-u Ezkar / Zikr first'
          : 'Failed to update prayer', isError: true);
    }
  }

  Future<void> _toggleEvrad(PrayerModel prayer) async {
    try {
      await PrayersApi.completePrayer(prayer.evradName);
      await _loadPrayers();
    } catch (e) {
      _showSnack('Failed to update Evrad', isError: true);
    }
  }

  void _showSnack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: isError ? AppColors.error : AppColors.primary,
      behavior: SnackBarBehavior.floating,
    ));
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
            const Text('Prayer Tracker',
                style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary)),
            Text(_getFormattedDate(),
                style: const TextStyle(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.normal)),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 16),
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.nights_stay_rounded,
                color: AppColors.primary, size: 24),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.primary))
          : RefreshIndicator(
              onRefresh: _loadPrayers,
              color: AppColors.primary,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildProgressCard(),
                    const SizedBox(height: 16),
                    if (_levelOrder >= 1) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppColors.accent.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                              color: AppColors.accent.withOpacity(0.2)),
                        ),
                        child: Row(children: [
                          const Icon(Icons.info_outline,
                              size: 16, color: AppColors.accent),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Your level requires Evrad-u Ezkar / Zikr before each prayer',
                              style: TextStyle(
                                  fontSize: 12, color: AppColors.accent),
                            ),
                          ),
                        ]),
                      ),
                      const SizedBox(height: 14),
                    ],
                    const Text("Today's Prayers",
                        style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 10),
                    ..._prayers.map((p) => _PrayerCard(
                          prayer: p,
                          onToggle: () => _togglePrayer(p),
                          onEvradToggle: () => _toggleEvrad(p),
                        )),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildProgressCard() {
    final total = _prayers.length;
    final progress = total > 0 ? _totalCompleted / total : 0.0;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, AppColors.primaryDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text("Today's Progress",
                style: TextStyle(color: Colors.white70, fontSize: 13)),
            Text('$_totalCompleted / $total prayers',
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold)),
          ]),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text('+$_totalPoints pts',
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600)),
          ),
        ]),
        const SizedBox(height: 14),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: Colors.white.withOpacity(0.3),
            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
            minHeight: 6,
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 4,
          runSpacing: 4,
          children: _prayers.map((p) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                p.isCompleted
                    ? Icons.check_circle_rounded
                    : Icons.circle_outlined,
                color: p.isCompleted ? Colors.white : Colors.white38,
                size: 14,
              ),
              const SizedBox(height: 2),
              Text(p.displayName.split(' ').first,
                  style: TextStyle(
                      color: p.isCompleted ? Colors.white : Colors.white54,
                      fontSize: 9)),
            ],
          )).toList(),
        ),
      ]),
    );
  }
}

class _PrayerCard extends StatelessWidget {
  final PrayerModel prayer;
  final VoidCallback onToggle;
  final VoidCallback onEvradToggle;

  const _PrayerCard({
    required this.prayer,
    required this.onToggle,
    required this.onEvradToggle,
  });

  @override
  Widget build(BuildContext context) {
    final isSpecial = prayer.name == 'duha' ||
        prayer.name == 'awwabin' ||
        prayer.name == 'qiyam';

    return ValueListenableBuilder<String?>(
      valueListenable: prayerTimeService.activePrayerNotifier,
      builder: (context, activePrayer, _) {
        final isActive = activePrayer == prayer.name &&
            !prayer.isCompleted;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: prayer.isCompleted
            ? AppColors.primary.withOpacity(0.03)
            : isActive
                ? const Color(0xFFEF9F27).withOpacity(0.08)
                : AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        boxShadow: isActive ? [
          BoxShadow(
            color: const Color(0xFFEF9F27).withOpacity(0.4),
            blurRadius: 12,
            spreadRadius: 2,
          )
        ] : null,
        border: Border.all(
          color: prayer.isCompleted
              ? AppColors.primary.withOpacity(0.3)
              : isActive
                  ? const Color(0xFFEF9F27).withOpacity(0.8)
                  : prayer.windowExpired
                  ? AppColors.error.withOpacity(0.2)
                  : AppColors.border,
        ),
      ),
      child: Column(children: [
        ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          leading: Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: prayer.isCompleted
                  ? AppColors.primary.withOpacity(0.1)
                  : isSpecial
                      ? AppColors.accent.withOpacity(0.08)
                      : AppColors.background,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              prayer.name == 'qiyam'
                  ? Icons.nightlight_round
                  : prayer.name == 'duha'
                      ? Icons.wb_sunny_outlined
                      : Icons.nights_stay_outlined,
              color: prayer.isCompleted
                  ? AppColors.primary
                  : isSpecial ? AppColors.accent : AppColors.textHint,
              size: 22,
            ),
          ),
          title: Text(prayer.displayName,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: prayer.isCompleted
                    ? AppColors.primary
                    : prayer.windowExpired
                        ? AppColors.textHint
                        : AppColors.textPrimary,
                decoration: prayer.windowExpired && !prayer.isCompleted
                    ? TextDecoration.lineThrough
                    : null,
              )),
          subtitle: Text(prayer.arabicName,
              style: TextStyle(
                  fontSize: 13,
                  color: prayer.isCompleted
                      ? AppColors.primary.withOpacity(0.7)
                      : AppColors.textSecondary)),
          trailing: Row(mainAxisSize: MainAxisSize.min, children: [
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(prayer.time,
                    style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textSecondary)),
                if (prayer.minutesLeft != null && !prayer.isCompleted)
                  Text('${prayer.minutesLeft}m left',
                      style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.error,
                          fontWeight: FontWeight.w500))
                else if (prayer.windowExpired && !prayer.isCompleted)
                  const Text('missed',
                      style: TextStyle(
                          fontSize: 11,
                          color: AppColors.error,
                          fontWeight: FontWeight.w500))
                else
                  Text('+${prayer.points} pts',
                      style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.accent,
                          fontWeight: FontWeight.w500)),
              ],
            ),
            const SizedBox(width: 12),
            GestureDetector(
              onTap: onToggle,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 28, height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: prayer.isCompleted
                      ? AppColors.primary
                      : prayer.isLocked
                          ? AppColors.border
                          : Colors.transparent,
                  border: Border.all(
                    color: prayer.isCompleted
                        ? AppColors.primary
                        : AppColors.border,
                    width: 2,
                  ),
                ),
                child: prayer.isCompleted
                    ? const Icon(Icons.check,
                        color: Colors.white, size: 16)
                    : prayer.isLocked
                        ? const Icon(Icons.lock,
                            color: AppColors.textHint, size: 14)
                        : null,
              ),
            ),
          ]),
        ),

        // Evrad sub-row
        if (prayer.evradRequired)
          Container(
            decoration: BoxDecoration(
              color: prayer.evradCompleted
                  ? AppColors.primary.withOpacity(0.04)
                  : AppColors.accent.withOpacity(0.04),
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(14),
                bottomRight: Radius.circular(14),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
              child: Row(children: [
                Container(
                  width: 30, height: 30,
                  decoration: BoxDecoration(
                    color: prayer.evradCompleted
                        ? AppColors.primary.withOpacity(0.1)
                        : AppColors.accent.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.auto_awesome,
                      color: prayer.evradCompleted
                          ? AppColors.primary
                          : AppColors.accent,
                      size: 15),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Evrad-u Ezkar / Zikr',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: prayer.evradCompleted
                                ? AppColors.primary
                                : AppColors.textSecondary,
                          )),
                      if (!prayer.evradCompleted && !prayer.isCompleted)
                        const Text('Check this first to unlock prayer',
                            style: TextStyle(
                                fontSize: 10,
                                color: AppColors.textHint)),
                    ],
                  ),
                ),
                Text('+${prayer.evradPoints} pts',
                    style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.accent,
                        fontWeight: FontWeight.w500)),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: onEvradToggle,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 24, height: 24,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: prayer.evradCompleted
                          ? AppColors.primary
                          : Colors.transparent,
                      border: Border.all(
                        color: prayer.evradCompleted
                            ? AppColors.primary
                            : AppColors.border,
                        width: 2,
                      ),
                    ),
                    child: prayer.evradCompleted
                        ? const Icon(Icons.check,
                            color: Colors.white, size: 13)
                        : null,
                  ),
                ),
              ]),
            ),
          ),
      ]),
    );
      }, // end ValueListenableBuilder builder
    ); // end ValueListenableBuilder
  }
}
