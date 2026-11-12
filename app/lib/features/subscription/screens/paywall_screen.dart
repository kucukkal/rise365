import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../core/services/subscription_service.dart';
import '../../../core/utils/log.dart';
import '../../../shared/models/user_model.dart';
import '../../home/screens/home_shell.dart';

/// Full-screen paywall shown when a logged-in user has no active subscription.
/// Apple requires:
///   • A "Restore Purchase" button/link visible on this screen
///   • Subscription price, duration, and auto-renewal terms clearly stated
///   • Links to Terms of Use and Privacy Policy
class PaywallScreen extends StatefulWidget {
  final UserModel user;
  const PaywallScreen({super.key, required this.user});

  @override
  State<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends State<PaywallScreen> {
  bool _loading = false;
  bool _restoring = false;
  String _priceStr = '\$5.99';

  static const _green = Color(0xFF1D9E75);
  static const _darkGreen = Color(0xFF16845F);

  @override
  void initState() {
    super.initState();
    _loadPrice();
  }

  Future<void> _loadPrice() async {
    final p = await SubscriptionService.yearlyPriceString();
    if (mounted && p != null) setState(() => _priceStr = p);
  }

  Future<void> _subscribe() async {
    setState(() => _loading = true);
    try {
      final ok = await SubscriptionService.purchase();
      if (!mounted) return;
      if (ok) {
        _goHome();
      } else {
        _show('Purchase was not completed. Please try again.');
      }
    } catch (e) {
      devLog('Paywall purchase error: $e');
      if (mounted) _show('Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _restore() async {
    setState(() => _restoring = true);
    try {
      final ok = await SubscriptionService.restore();
      if (!mounted) return;
      if (ok) {
        _goHome();
      } else {
        _show('No previous purchase found for this Apple ID.');
      }
    } catch (e) {
      devLog('Paywall restore error: $e');
      if (mounted) _show('Restore failed. Please try again.');
    } finally {
      if (mounted) setState(() => _restoring = false);
    }
  }

  void _goHome() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => HomeShell(user: widget.user)),
    );
  }

  void _show(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _green,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // ── header ───────────────────────────────────────────────────
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(22),
                child: Image.asset(
                  'assets/icon/icon.png',
                  width: 84,
                  height: 84,
                  fit: BoxFit.cover,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Rise365',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Daily Habits · Stronger Faith',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.85),
                  fontSize: 15,
                ),
              ),
              const SizedBox(height: 32),

              // ── feature card ─────────────────────────────────────────────
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                    horizontal: 20, vertical: 24),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withOpacity(0.22)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Everything in Rise365',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.9),
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.6,
                      ),
                    ),
                    const SizedBox(height: 16),
                    ..._features.map(_featureRow),
                  ],
                ),
              ),
              const SizedBox(height: 28),

              // ── price badge ───────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 18, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Text(
                  '$_priceStr / year',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Auto-renews annually. Cancel anytime.',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 28),

              // ── CTA button ────────────────────────────────────────────────
              SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton(
                  onPressed: _loading ? null : _subscribe,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: _darkGreen,
                    disabledBackgroundColor: Colors.white60,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: _loading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Color(0xFF1D9E75),
                          ),
                        )
                      : const Text(
                          'Subscribe for $_staticPriceLabel',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 18),

              // ── restore ───────────────────────────────────────────────────
              GestureDetector(
                onTap: _restoring ? null : _restore,
                child: _restoring
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white70,
                        ),
                      )
                    : Text(
                        'Restore Purchase',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.75),
                          fontSize: 14,
                          decoration: TextDecoration.underline,
                          decorationColor: Colors.white54,
                        ),
                      ),
              ),
              const SizedBox(height: 28),

              // ── legal links (required by Apple) ───────────────────────────
              RichText(
                textAlign: TextAlign.center,
                text: TextSpan(
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 11,
                    height: 1.6,
                  ),
                  children: [
                    const TextSpan(
                        text:
                            'By subscribing you agree to our\n'),
                    TextSpan(
                      text: 'Terms of Use',
                      style: const TextStyle(
                          decoration: TextDecoration.underline),
                      recognizer: TapGestureRecognizer()
                        ..onTap = () => launchUrl(
                              Uri.parse('https://www.apple.com/legal/internet-services/itunes/dev/stdeula/'),
                              mode: LaunchMode.externalApplication,
                            ),
                    ),
                    const TextSpan(text: '  ·  '),
                    TextSpan(
                      text: 'Privacy Policy',
                      style: const TextStyle(
                          decoration: TextDecoration.underline),
                      recognizer: TapGestureRecognizer()
                        ..onTap = () => launchUrl(
                              Uri.parse('https://rise365.app/privacy'),
                              mode: LaunchMode.externalApplication,
                            ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  static const _staticPriceLabel = '\$5.99 / year';

  static const _features = [
    ('📋', 'Daily tasks & progress tracking'),
    ('🕌', 'Prayer logging with points'),
    ('👥', 'Circles — group accountability'),
    ('🏆', 'Circle contests & leaderboards'),
    ('📈', 'Weekly & monthly reports'),
    ('🔔', 'Smart daily reminders'),
  ];

  Widget _featureRow((String, String) item) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Text(item.$1, style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              item.$2,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
