import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/notification_navigation.dart';
import '../../../core/services/prayer_time_service.dart';
import '../../../shared/models/user_model.dart';
import '../../tasks/screens/tasks_screen.dart';
import '../../prayer/screens/prayer_screen.dart';
import '../../events/screens/events_screen.dart';
import '../../profile/screens/profile_screen.dart';
import '../../circles/screens/circles_screen.dart';

class HomeShell extends StatefulWidget {
  final UserModel user;
  final String initialFrequency;
  const HomeShell({
    super.key,
    required this.user,
    this.initialFrequency = 'daily',
  });

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _currentIndex = 0;
  String _taskFrequency = 'daily';

  @override
  void initState() {
    super.initState();
    _taskFrequency = widget.initialFrequency;
    notificationTabNotifier.addListener(_onNotificationNav);
  }

  void _onNotificationNav() {
    final nav = notificationTabNotifier.value;
    if (mounted) {
      setState(() {
        _currentIndex = nav.tabIndex;
        _taskFrequency = nav.frequency;
      });
    }
  }

  @override
  void dispose() {
    notificationTabNotifier.removeListener(_onNotificationNav);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: IndexedStack(
        index: _currentIndex,
        children: [
          TasksScreen(
            user: widget.user,
            initialFrequency: _taskFrequency,
          ),
          PrayerScreen(user: widget.user),
          EventsScreen(user: widget.user),
          const CirclesScreen(),
          ProfileScreen(user: widget.user),
        ],
      ),
      bottomNavigationBar: ValueListenableBuilder<String?>(
        valueListenable: prayerTimeService.activePrayerNotifier,
        builder: (context, activePrayer, _) {
          return Container(
            decoration: const BoxDecoration(
              border: Border(
                  top: BorderSide(color: AppColors.border, width: 0.5)),
            ),
            child: Stack(
              children: [
                BottomNavigationBar(
                  currentIndex: _currentIndex,
                  onTap: (i) => setState(() => _currentIndex = i),
                  backgroundColor: AppColors.surface,
                  selectedItemColor: AppColors.primary,
                  unselectedItemColor: AppColors.textHint,
                  elevation: 0,
                  type: BottomNavigationBarType.fixed,
                  selectedFontSize: 11,
                  unselectedFontSize: 11,
                  items: const [
                    BottomNavigationBarItem(
                      icon: Icon(Icons.check_circle_outline_rounded),
                      activeIcon: Icon(Icons.check_circle_rounded),
                      label: 'Tasks',
                    ),
                    BottomNavigationBarItem(
                      icon: Icon(Icons.nights_stay_outlined),
                      activeIcon: Icon(Icons.nights_stay_rounded),
                      label: 'Prayer',
                    ),
                    BottomNavigationBarItem(
                      icon: Icon(Icons.event_outlined),
                      activeIcon: Icon(Icons.event_rounded),
                      label: 'Events',
                    ),
                    BottomNavigationBarItem(
                      icon: Icon(Icons.groups_2_outlined),
                      activeIcon: Icon(Icons.groups_2_rounded),
                      label: 'Circles',
                    ),
                    BottomNavigationBarItem(
                      icon: Icon(Icons.person_outline_rounded),
                      activeIcon: Icon(Icons.person_rounded),
                      label: 'Profile',
                    ),
                  ],
                ),
                // Gold dot badge on Prayer tab when prayer time active
                if (activePrayer != null)
                  Positioned(
                    // Prayer tab is index 1 of 5 tabs (center at 1.5/5 of the width)
                    left: MediaQuery.of(context).size.width * 0.30 - 5,
                    top: 6,
                    child: Container(
                      width: 10,
                      height: 10,
                      decoration: const BoxDecoration(
                        color: Color(0xFFEF9F27),
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}
