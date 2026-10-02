import 'package:rise365/core/utils/log.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/auth_api.dart';
import 'otp_screen.dart';
import 'package:dio/dio.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  Map<String, dynamic> _signupInfo = {
    'welcome_message': 'Welcome to Rise 365! How would you like to begin your journey? Every journey starts with a single step. Choose the path that feels right for you today.',
    'myseed_title': '🌱 MySeed Path',
    'myseed_description': 'Start gently with a simple, sustainable routine — just the essentials. Plant your seed of goodness with signup code "MySeed"',
    'myrise_title': '🌿 MyBuild Path',
    'myrise_description': 'Create a routine that matches your goals and builds upon MySeed. Build your rise with signup code "MyBuild"',
  };
  final _phoneController = TextEditingController();
  final _codeController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  void _continue() async {
  if (!_formKey.currentState!.validate()) return;
  setState(() => _isLoading = true);
  try {
    // Format phone number with +1 if not already there
    String phone = _phoneController.text.trim();
    if (!phone.startsWith('+')) {
      phone = '+1$phone';
    }
    devLog('📱 Sending OTP to: $phone with code: ${_codeController.text.trim()}');
    final result = await AuthApi.sendOtp(
      phone: phone,
      signupCode: _codeController.text.trim(),
    );
    devLog('📱 OTP result: $result');
    if (mounted) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => OtpScreen(
            phone: phone,
            signupCode: _codeController.text.trim(),
            codeType: result['code_type'] ?? 'custom',
          ),
        ),
      );
    }
  } catch (e) {
  devLog('❌ Error type: ${e.runtimeType}');
  devLog('❌ Error: $e');
  String errorMsg = 'Something went wrong';
  if (e is DioException) {
    devLog('❌ Status: ${e.response?.statusCode}');
    devLog('❌ Data: ${e.response?.data}');
    errorMsg = e.response?.data?['detail'] ?? e.message ?? errorMsg;
  }
  if (mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(errorMsg),
        backgroundColor: AppColors.error,
      ),
    );
  }
}
  setState(() => _isLoading = false);
}
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 60),

                // Logo
                Center(
                  child: Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(22),
                    ),
                    child: const Icon(
                      Icons.wb_sunny_rounded,
                      size: 48,
                      color: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // Title
                const Text(
                  'Welcome to\nRise365',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Enter your phone number to get started',
                  style: TextStyle(
                    fontSize: 15,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 24),

                // Dynamic signup path info from admin
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: AppColors.primary.withOpacity(0.2)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _signupInfo['welcome_message'] ?? '',
                        style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary),
                      ),
                      const SizedBox(height: 14),
                      // MySeed card
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _signupInfo['myseed_title'] ?? '🌱 MySeed Path',
                              style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.primary),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              _signupInfo['myseed_description'] ?? '',
                              style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                      // MyBuild card
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _signupInfo['myrise_title'] ?? '🌿 MyBuild Path',
                              style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.primary),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              _signupInfo['myrise_description'] ?? '',
                              style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Signup code field
                const Text(
                  'Signup Code',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _codeController,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: const InputDecoration(
                    hintText: 'Enter your invite code',
                    prefixIcon: Icon(Icons.key_outlined,
                        color: AppColors.textHint),
                  ),
                  validator: (v) =>
                      v == null || v.isEmpty ? 'Please enter your invite code' : null,
                ),
                const SizedBox(height: 20),

                // Phone field
                const Text(
                  'Phone Number',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: const InputDecoration(
                    hintText: '+1 (555) 000-0000',
                    prefixIcon: Icon(Icons.phone_outlined,
                        color: AppColors.textHint),
                  ),
                  validator: (v) =>
                      v == null || v.length < 10 ? 'Enter a valid phone number' : null,
                ),
                const SizedBox(height: 32),

                // Button
                ElevatedButton(
                  onPressed: _isLoading ? null : _continue,
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : const Text('Send Verification Code'),
                ),
                const SizedBox(height: 24),

                // Footer note
                Center(
                  child: Text(
                    'You need an invite code to join Rise365',
                    style: TextStyle(
                      fontSize: 13,
                      color: AppColors.textHint,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}