import 'package:rise365/core/utils/log.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/services/auth_api.dart';
import '../../../core/services/users_api.dart';
import '../../../shared/models/user_model.dart';
import '../../home/screens/home_shell.dart';
import 'questionnaire_screen.dart';

class RegisterScreen extends StatefulWidget {
  final String phone;
  final String codeType;
  final String signupCode;
  final String verificationToken;

  const RegisterScreen({
    super.key,
    required this.phone,
    this.codeType = 'custom',
    this.signupCode = '',
    this.verificationToken = '',
  });

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _zipController = TextEditingController();
  bool _useZip = true;
  final _cityController = TextEditingController();
  final _stateController = TextEditingController();

  String get _fullName =>
      '${_firstNameController.text.trim()} ${_lastNameController.text.trim()}'.trim();
  String? _selectedLevelId;
  bool _isLoading = false;
  bool _levelsLoading = true;
  List<Map<String, dynamic>> _levels = [];

  @override
  void initState() {
    super.initState();
    _loadLevels();
  }

  Future<void> _loadLevels() async {
    try {
      final response = await ApiService.dio.get('/auth/levels');
      final List<dynamic> data = response.data;
      setState(() {
        _levels = data
            .where((l) {
              final lt = l['level_type']?.toString() ?? 'custom';
              return lt == 'custom';
            })
            .map((l) => {
                  'id': l['id'].toString(),
                  'name': l['name'].toString(),
                  'description': (l['description'] ?? '').toString(),
                })
            .toList();
        _levelsLoading = false;
      });
    } catch (e) {
      setState(() {
        _levels = [];
        _levelsLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _zipController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    super.dispose();
  }

  Future<void> _saveFcmToken() async {
    try {
      final messaging = FirebaseMessaging.instance;
      final token = await messaging.getToken();
      if (token != null) {
        await UsersApi.updateFcmToken(token);
      }
    } catch (e) {
      devLog('FCM token error: $e');
    }
  }

  String _errorMessage(Object e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] is String) return data['detail'];
    }
    return 'Something went wrong. Please try again.';
  }

  void _register() async {
    if (_firstNameController.text.trim().isEmpty ||
        _lastNameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your first and last name')));
      return;
    }

    final zip = _zipController.text.trim();
    final city = _cityController.text.trim();
    final st = _stateController.text.trim().toUpperCase();
    final zipOk = _useZip;
    final locationValid = _useZip
        ? RegExp(r'^\d{5}$').hasMatch(zip)
        : (city.isNotEmpty && st.length == 2);
    if (!locationValid) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(_useZip
              ? 'Please enter your 5-digit ZIP code'
              : 'Please enter your city and 2-letter state')));
      return;
    }

    FocusScope.of(context).unfocus();
    setState(() => _isLoading = true);

    try {
      // Determine level ID
      String levelId;
      if (widget.codeType == 'myseed' || widget.codeType == 'myrise') {
        levelId = widget.signupCode;
      } else {
        levelId = _selectedLevelId ??
            (_levels.isNotEmpty ? _levels.first['id'] : 'level_1');
      }

      devLog('📱 Registering with: phone=${widget.phone}, name=$_fullName, levelId=$levelId, codeType=${widget.codeType}, signupCode=${widget.signupCode}');

      final response = await AuthApi.register(
        phone: widget.phone,
        name: _fullName,
        firstName: _firstNameController.text.trim(),
        lastName: _lastNameController.text.trim(),
        programLevelId: levelId,
        verificationToken: widget.verificationToken,
        zipCode: zipOk ? zip : null,
        city: zipOk ? null : city,
        state: zipOk ? null : st,
      );
      
      devLog('📱 Registration response: $response');

      final user = UserModel(
        id: response['user_id'] ?? '',
        name: response['name'] ?? '',
        phone: widget.phone,
        programLevel: response['program_level'] ?? '',
        totalPoints: response['total_points'] ?? 0,
        completionRate:
            (response['completion_rate'] ?? 0.0).toDouble(),
      );

      // Save FCM token
      await _saveFcmToken();

      if (!mounted) return;

      // Route based on code type
      if (widget.codeType == 'myrise') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => QuestionnaireScreen(user: user),
          ),
        );
      } else {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => HomeShell(user: user)),
          (route) => false,
        );
      }
    } catch (e) {
      devLog('❌ Registration error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage(e)),
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
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new,
              color: AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 16),
                    const Text(
                      'Create your\nprofile',
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Tell us about yourself to get started',
                      style: TextStyle(
                        fontSize: 15,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 32),

                    // First name
                    const Text('First Name',
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _firstNameController,
                      textCapitalization: TextCapitalization.words,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        hintText: 'Enter your first name',
                        prefixIcon: Icon(Icons.person_outline,
                            color: AppColors.textHint),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Last name
                    const Text('Last Name',
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _lastNameController,
                      textCapitalization: TextCapitalization.words,
                      decoration: const InputDecoration(
                        hintText: 'Enter your last name',
                        prefixIcon: Icon(Icons.person_outline,
                            color: AppColors.textHint),
                      ),
                    ),

                    // Location (required: ZIP code OR city & state)
                    const SizedBox(height: 24),
                    const Text('Your Location',
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 4),
                    const Text('Required for accurate prayer times.',
                        style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                    const SizedBox(height: 10),
                    SegmentedButton<bool>(
                      showSelectedIcon: false,
                      segments: const [
                        ButtonSegment(value: true, label: Text('ZIP code')),
                        ButtonSegment(value: false, label: Text('City & State')),
                      ],
                      selected: {_useZip},
                      onSelectionChanged: (s) => setState(() => _useZip = s.first),
                    ),
                    const SizedBox(height: 10),
                    if (_useZip)
                      TextField(
                        controller: _zipController,
                        keyboardType: TextInputType.number,
                        maxLength: 5,
                        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                        decoration: const InputDecoration(
                          hintText: 'ZIP code (e.g. 20170)',
                          counterText: '',
                          prefixIcon: Icon(Icons.location_on_outlined,
                              color: AppColors.textHint),
                        ),
                      )
                    else
                      Row(children: [
                        Expanded(
                          flex: 3,
                          child: TextField(
                            controller: _cityController,
                            textCapitalization: TextCapitalization.words,
                            decoration: const InputDecoration(hintText: 'City'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 2,
                          child: TextField(
                            controller: _stateController,
                            textCapitalization: TextCapitalization.characters,
                            maxLength: 2,
                            decoration: const InputDecoration(
                                hintText: 'State (VA)', counterText: ''),
                          ),
                        ),
                      ]),

                    // Level selection — only for custom codes
                    if (widget.codeType == 'custom') ...[
                      const SizedBox(height: 28),
                      const Text('Select Your Program Level',
                          style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: AppColors.textPrimary)),
                      const SizedBox(height: 4),
                      const Text(
                          'Your admin assigns tasks based on your level',
                          style: TextStyle(
                              fontSize: 12,
                              color: AppColors.textSecondary)),
                      const SizedBox(height: 12),
                      if (_levelsLoading)
                        const Center(
                          child: Padding(
                            padding: EdgeInsets.all(24),
                            child: CircularProgressIndicator(
                                color: AppColors.primary),
                          ),
                        )
                      else if (_levels.isEmpty)
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.surface,
                            borderRadius:
                                BorderRadius.circular(12),
                            border: Border.all(
                                color: AppColors.border),
                          ),
                          child: const Text(
                            'No levels available yet. Please contact your admin.',
                            style: TextStyle(
                                fontSize: 13,
                                color: AppColors.textSecondary),
                          ),
                        )
                      else
                        ..._levels.map((level) {
                          final isSelected =
                              _selectedLevelId == level['id'];
                          return GestureDetector(
                            onTap: () => setState(() =>
                                _selectedLevelId = level['id']),
                            child: AnimatedContainer(
                              duration:
                                  const Duration(milliseconds: 200),
                              margin:
                                  const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? AppColors.primary
                                        .withOpacity(0.08)
                                    : AppColors.surface,
                                borderRadius:
                                    BorderRadius.circular(12),
                                border: Border.all(
                                  color: isSelected
                                      ? AppColors.primary
                                      : AppColors.border,
                                  width: isSelected ? 2 : 1,
                                ),
                              ),
                              child: Row(children: [
                                Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: isSelected
                                        ? AppColors.primary
                                        : AppColors.background,
                                    borderRadius:
                                        BorderRadius.circular(10),
                                  ),
                                  child: Icon(
                                    Icons.star_rounded,
                                    color: isSelected
                                        ? Colors.white
                                        : AppColors.textHint,
                                    size: 20,
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        level['name']!,
                                        style: TextStyle(
                                          fontSize: 14,
                                          fontWeight:
                                              FontWeight.w600,
                                          color: isSelected
                                              ? AppColors.primary
                                              : AppColors
                                                  .textPrimary,
                                        ),
                                      ),
                                      if ((level['description'] ??
                                              '')
                                          .isNotEmpty)
                                        Text(
                                          level['description']!,
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: isSelected
                                                ? AppColors.primary
                                                : AppColors
                                                    .textSecondary,
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                                if (isSelected)
                                  const Icon(
                                    Icons.check_circle,
                                    color: AppColors.primary,
                                    size: 22,
                                  ),
                              ]),
                            ),
                          );
                        }),
                    ],

                    // Path info for MySeed/MyBuild
                    if (widget.codeType == 'myseed') ...[
                      const SizedBox(height: 24),
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.06),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                              color:
                                  AppColors.primary.withOpacity(0.2)),
                        ),
                        child: Row(children: [
                          const Text('🌱',
                              style: TextStyle(fontSize: 24)),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment:
                                  CrossAxisAlignment.start,
                              children: [
                                Text('MySeed Path',
                                    style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.primary)),
                                Text(
                                    'Your tasks and rank will be set up by your admin.',
                                    style: TextStyle(
                                        fontSize: 12,
                                        color:
                                            AppColors.textSecondary)),
                              ],
                            ),
                          ),
                        ]),
                      ),
                    ],

                    if (widget.codeType == 'myrise') ...[
                      const SizedBox(height: 24),
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.06),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                              color:
                                  AppColors.primary.withOpacity(0.2)),
                        ),
                        child: Row(children: [
                          const Text('🌿',
                              style: TextStyle(fontSize: 24)),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment:
                                  CrossAxisAlignment.start,
                              children: [
                                Text('MyBuild Path',
                                    style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.primary)),
                                Text(
                                    'Next: a short questionnaire to determine your rank, then choose your tasks.',
                                    style: TextStyle(
                                        fontSize: 12,
                                        color:
                                            AppColors.textSecondary)),
                              ],
                            ),
                          ),
                        ]),
                      ),
                    ],

                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
              child: SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _register,
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2))
                      : const Text('Create Profile'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
