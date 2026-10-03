import 'package:rise365/core/utils/log.dart';
import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/models/user_model.dart';
import '../../../core/services/api_service.dart';
import '../../../core/services/users_api.dart';
import '../../auth/screens/login_screen.dart';

class ProfileScreen extends StatefulWidget {
  final UserModel user;
  const ProfileScreen({super.key, required this.user});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  UserModel? _freshUser;
  bool _isLoading = false;

  UserModel get user => _freshUser ?? widget.user;

  @override
  void initState() {
    super.initState();
    _refreshProfile();
  }

  Future<void> _refreshProfile() async {
    setState(() => _isLoading = true);
    try {
      final data = await UsersApi.getProfile();
      if (mounted) {
        setState(() {
          _freshUser = UserModel(
            id: data['id'] ?? user.id,
            name: data['name'] ?? user.name,
            phone: data['phone'] ?? user.phone,
            programLevel: data['program_level'] ?? user.programLevel,
            totalPoints: data['total_points'] ?? user.totalPoints,
            completionRate: (data['completion_rate'] ?? user.completionRate).toDouble(),
          );
        });
      }
    } catch (e) {
      devLog('Profile refresh error: $e');
    }
    setState(() => _isLoading = false);
  }

  Future<void> _confirmDeleteAccount() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete account?'),
        content: const Text(
          'This permanently deletes your account, progress, prayer history '
          'and events. This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete',
                style: TextStyle(color: AppColors.error,
                    fontWeight: FontWeight.w600))),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await ApiService.dio.delete('/users/me');
      await ApiService.clearToken();
      if (!mounted) return;
      Navigator.of(context, rootNavigator: true).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Could not delete your account. Please try again.'),
        backgroundColor: AppColors.error,
      ));
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

  String _nextLevel(String current) {
    const levels = ['Starter', 'Bronze', 'Silver', 'Gold', 'Sapphire', 'Diamond'];
    final idx = levels.indexOf(current);
    return idx == levels.length - 1 ? 'Max Level' : levels[idx + 1];
  }

  double _progressToNext(double rate) {
    if (rate >= 91) return 1.0;
    if (rate >= 81) return (rate - 81) / 10;
    if (rate >= 71) return (rate - 71) / 10;
    if (rate >= 60) return (rate - 60) / 10;
    if (rate >= 50) return (rate - 50) / 10;
    return rate / 50;
  }

  @override
  Widget build(BuildContext context) {
    final level = user.achievementLevel;
    final color = _achievementColor(level);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(padding: EdgeInsets.zero, children: [
          // Header
          Container(
            color: AppColors.surface,
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
            child: Column(children: [
              Container(
                width: 80, height: 80,
                decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle),
                child: Center(
                  child: Text(
                    user.name.isNotEmpty ? user.name[0].toUpperCase() : 'U',
                    style: const TextStyle(color: Colors.white, fontSize: 32,
                        fontWeight: FontWeight.bold),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(user.name,
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 4),
              Text(user.programLevel,
                  style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: color.withOpacity(0.3)),
                ),
                child: Text('⭐ $level',
                    style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 14)),
              ),
            ]),
          ),
          const SizedBox(height: 12),

          // Stats
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(children: [
              _StatCard(label: 'Total Points', value: '${user.totalPoints}',
                  icon: Icons.stars_rounded, color: AppColors.accent),
              const SizedBox(width: 10),
              _StatCard(label: 'Completion', value: '${user.completionRate.toInt()}%',
                  icon: Icons.pie_chart_rounded, color: AppColors.primary),
            ]),
          ),
          const SizedBox(height: 12),

          // Progress card — same green as the avatar, white text
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Achievement Progress',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600,
                      color: Colors.white)),
              const SizedBox(height: 14),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text(level, style: const TextStyle(fontSize: 13,
                    fontWeight: FontWeight.w600, color: Colors.white)),
                Text(_nextLevel(level),
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500,
                        color: Colors.white.withOpacity(0.8))),
              ]),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progressToNext(user.completionRate),
                  backgroundColor: Colors.white.withOpacity(0.25),
                  valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                  minHeight: 8,
                ),
              ),
              const SizedBox(height: 8),
              Text('${user.completionRate.toInt()}% completion rate',
                  style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.85))),
            ]),
          ),
          const SizedBox(height: 12),

          // Levels legend
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Achievement Levels',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 14),
              _LevelRow(name: 'Starter', range: '0% – 49%', color: AppColors.starter, current: level),
              _LevelRow(name: 'Bronze', range: '50% – 59%', color: AppColors.bronze, current: level),
              _LevelRow(name: 'Silver', range: '60% – 70%', color: AppColors.silver, current: level),
              _LevelRow(name: 'Gold', range: '71% – 80%', color: AppColors.gold, current: level),
              _LevelRow(name: 'Sapphire', range: '81% – 90%', color: AppColors.sapphire, current: level),
              _LevelRow(name: 'Diamond', range: '91% – 100%', color: AppColors.diamond, current: level),
            ]),
          ),
          const SizedBox(height: 24),

          // Delete account (required by Apple)
          Center(
            child: TextButton.icon(
              onPressed: _confirmDeleteAccount,
              icon: const Icon(Icons.delete_outline,
                  color: AppColors.error, size: 18),
              label: const Text('Delete account',
                  style: TextStyle(color: AppColors.error, fontSize: 13)),
            ),
          ),
          const SizedBox(height: 32),
        ]),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  const _StatCard({required this.label, required this.value,
      required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color)),
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ]),
      ),
    );
  }
}

class _LevelRow extends StatelessWidget {
  final String name;
  final String range;
  final Color color;
  final String current;
  const _LevelRow({required this.name, required this.range,
      required this.color, required this.current});

  @override
  Widget build(BuildContext context) {
    final isActive = name == current;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isActive ? color.withOpacity(0.08) : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: isActive ? color.withOpacity(0.3) : Colors.transparent),
      ),
      child: Row(children: [
        Container(width: 10, height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 10),
        Text(name, style: TextStyle(
          fontSize: 13,
          fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
          color: isActive ? color : AppColors.textSecondary,
        )),
        const Spacer(),
        Text(range, style: TextStyle(
            fontSize: 12, color: isActive ? color : AppColors.textHint)),
        if (isActive) ...[
          const SizedBox(width: 8),
          Icon(Icons.check_circle_rounded, color: color, size: 16),
        ],
      ]),
    );
  }
}