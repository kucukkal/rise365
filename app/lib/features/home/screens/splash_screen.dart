import 'package:rise365/core/utils/log.dart';
import 'package:flutter/material.dart';
import '../../../core/services/api_service.dart';
import '../../../core/services/users_api.dart';
import '../../../shared/models/user_model.dart';
import '../../auth/screens/login_screen.dart';
import 'home_shell.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnim;
  late Animation<double> _scaleAnim;
  String _quoteText = '';
  String _quoteSource = '';

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _fadeAnim = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn));
    _scaleAnim = Tween<double>(begin: 0.85, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));
    _controller.forward();
    _loadQuote();
    _initialize();
  }

  Future<void> _loadQuote() async {
    try {
      final response = await ApiService.dio.get('/quotes/random');
      if (mounted) {
        setState(() {
          _quoteText = response.data['text'] ?? '';
          _quoteSource = response.data['source'] ?? '';
        });
      }
    } catch (e) {
      devLog('Quote error: $e');
    }
  }

  Future<void> _initialize() async {
    await Future.delayed(const Duration(milliseconds: 2500));

    if (!mounted) return;

    try {
      final isLoggedIn = await ApiService.isLoggedIn();
      if (isLoggedIn) {
        try {
          final data = await UsersApi.getProfile()
              .timeout(const Duration(seconds: 8));
          if (!mounted) return;
          final user = UserModel(
            id: data['id'] ?? '',
            name: data['name'] ?? '',
            phone: data['phone'] ?? '',
            programLevel: data['program_level'] ?? '',
            totalPoints: data['total_points'] ?? 0,
            completionRate: (data['completion_rate'] ?? 0.0).toDouble(),
            achievementLevel: data['achievement_level'] ?? 'Starter',
          );
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (_) => HomeShell(user: user),
            ),
          );
        } catch (e) {
          await ApiService.clearToken();
          if (mounted) {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (_) => const LoginScreen()),
            );
          }
        }
      } else {
        if (mounted) {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => const LoginScreen()),
          );
        }
      }
    } catch (e) {
      await ApiService.clearToken();
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const LoginScreen()),
        );
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1D9E75),
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: ScaleTransition(
            scale: _scaleAnim,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(26),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.18),
                        blurRadius: 18,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(26),
                    child: Image.asset(
                      'assets/icon/icon.png',
                      width: 104,
                      height: 104,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Rise365',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 36,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Your daily spiritual journey',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 16,
                  ),
                ),
                if (_quoteText.isNotEmpty) ...[
                  const SizedBox(height: 48),
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 32),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                          color: Colors.white.withOpacity(0.2)),
                    ),
                    child: Column(
                      children: [
                        Text(
                          '"$_quoteText"',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.95),
                            fontSize: 14,
                            fontStyle: FontStyle.italic,
                            height: 1.5,
                          ),
                        ),
                        if (_quoteSource.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            '— $_quoteSource',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.7),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
