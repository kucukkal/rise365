import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/auth_api.dart';
import 'register_screen.dart';

class OtpScreen extends StatefulWidget {
  final String phone;
  final String signupCode;
  final String codeType;
  const OtpScreen({
    super.key,
    required this.phone,
    this.signupCode = '',
    this.codeType = 'custom',
  });

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  // Single controller behind 6 visual boxes — fixes backspace + SMS auto-fill
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() {}); // redraw boxes on each keystroke
      if (_controller.text.length == 6) _verify();
    });
    // Auto-focus the hidden field on open
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    final otp = _controller.text;
    if (otp.length < 6) return;
    if (_isLoading) return;

    setState(() => _isLoading = true);
    try {
      final verifyResult = await AuthApi.verifyOtp(
        phone: widget.phone,
        code: otp,
      );
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => RegisterScreen(
            phone: widget.phone,
            signupCode: widget.signupCode,
            codeType: widget.codeType,
            verificationToken:
                verifyResult['verification_token']?.toString() ?? '',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      _controller.clear();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Invalid code. Please try again.'),
          backgroundColor: AppColors.error,
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final code = _controller.text;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new,
              color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: GestureDetector(
        // Tap anywhere to refocus hidden field
        onTap: () => _focusNode.requestFocus(),
        behavior: HitTestBehavior.opaque,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),
                const Text(
                  'Verify your number',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'We sent a 6-digit code to\n${widget.phone}',
                  style: const TextStyle(
                    fontSize: 15,
                    color: AppColors.textSecondary,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 40),

                // ── 6 visual boxes ────────────────────────────────────────
                Stack(
                  children: [
                    // Hidden real input (receives keyboard / SMS auto-fill)
                    Opacity(
                      opacity: 0,
                      child: TextField(
                        controller: _controller,
                        focusNode: _focusNode,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        autofillHints: const [AutofillHints.oneTimeCode],
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly
                        ],
                        onSubmitted: (_) => _verify(),
                      ),
                    ),
                    // Visual boxes row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: List.generate(6, (i) {
                        final filled = i < code.length;
                        final isActive =
                            i == code.length && _focusNode.hasFocus;
                        return GestureDetector(
                          onTap: () => _focusNode.requestFocus(),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 150),
                            width: 48,
                            height: 56,
                            decoration: BoxDecoration(
                              color: AppColors.surface,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: isActive
                                    ? AppColors.primary
                                    : filled
                                        ? AppColors.primary.withOpacity(0.5)
                                        : AppColors.border,
                                width: isActive ? 2 : 1,
                              ),
                            ),
                            alignment: Alignment.center,
                            child: filled
                                ? Text(
                                    code[i],
                                    style: const TextStyle(
                                      fontSize: 22,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.textPrimary,
                                    ),
                                  )
                                : isActive
                                    ? Container(
                                        width: 2,
                                        height: 24,
                                        color: AppColors.primary,
                                      )
                                    : null,
                          ),
                        );
                      }),
                    ),
                  ],
                ),

                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    onPressed: (_isLoading || code.length < 6)
                        ? null
                        : _verify,
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2))
                        : const Text('Verify Code'),
                  ),
                ),
                const SizedBox(height: 20),
                Center(
                  child: TextButton(
                    onPressed: () {},
                    child: const Text(
                      'Resend code',
                      style: TextStyle(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w500),
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
