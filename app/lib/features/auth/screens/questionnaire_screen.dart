import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../shared/models/user_model.dart';
import '../../home/screens/home_shell.dart';
import 'task_selection_screen.dart';

class QuestionnaireScreen extends StatefulWidget {
  final UserModel user;
  const QuestionnaireScreen({super.key, required this.user});

  @override
  State<QuestionnaireScreen> createState() => _QuestionnaireScreenState();
}

class _QuestionnaireScreenState extends State<QuestionnaireScreen> {
  int _currentQuestion = 0;
  bool? _q1;
  bool? _q2;
  bool? _q3;
  int? _q4;
  bool _isLoading = false;
  int? _determinedRank;

  final List<Map<String, dynamic>> _questions = [
    {
      'question': 'Do you pray all 5 daily obligatory prayers regularly?',
      'subtitle': 'Fajr, Dhuhr, Asr, Maghrib, Isha',
      'type': 'bool',
      'options': ['Not yet / Sometimes', 'Yes, consistently'],
    },
    {
      'question': 'Do you perform Evrad-u Ezkar / Zikr after each prayer?',
      'subtitle': 'Dhikr and remembrance after every obligatory prayer',
      'type': 'bool',
      'options': ['No / Sometimes', 'Yes, always'],
    },
    {
      'question': 'Do you complete your prayers and Zikr within 45 minutes of prayer time?',
      'subtitle': 'Starting from the call to prayer (Adhan)',
      'type': 'bool',
      'options': ['Not always', 'Yes, usually'],
    },
    {
      'question': 'Do you perform any voluntary prayers?',
      'subtitle': 'Salat-ul Duha, Ṣalāt al-Awwābīn, or Qiyam al-Layl',
      'type': 'int',
      'options': ['None', 'One of them', 'Two or more'],
    },
  ];

  int _determineRank() {
    if (_q1 == false || _q2 == false) return 0;
    if (_q3 == false) return 1;
    if (_q4 == 0) return 2;
    if (_q4 == 1) return 3;
    return 4;
  }

  String _getRankName(int rank) {
    switch (rank) {
      case 0: return 'MyRise — Beginner';
      case 1: return 'MyRise — Dedicated';
      case 2: return 'MyRise — Committed';
      case 3: return 'MyRise — Advanced';
      case 4: return 'MyRise — Elite';
      default: return 'MyRise';
    }
  }

  String _getRankDescription(int rank) {
    switch (rank) {
      case 0: return 'You\'ll start with the 5 daily obligatory prayers.';
      case 1: return 'Prayers + Evrad/Zikr after each prayer.';
      case 2: return 'Prayers + Evrad/Zikr within 45 minutes.';
      case 3: return 'Rank 2 + 1 voluntary prayer.';
      case 4: return 'Rank 2 + 2 voluntary prayers.';
      default: return '';
    }
  }

  void _answerQuestion(dynamic answer) {
    setState(() {
      if (_currentQuestion == 0) _q1 = answer as bool;
      if (_currentQuestion == 1) _q2 = answer as bool;
      if (_currentQuestion == 2) _q3 = answer as bool;
      if (_currentQuestion == 3) _q4 = answer as int;

      // Check early exit conditions
      if (_currentQuestion == 0 && _q1 == false) {
        _q2 = false; _q3 = false; _q4 = 0;
        _determinedRank = 0;
        _currentQuestion = _questions.length; // skip to result
        return;
      }
      if (_currentQuestion == 1 && _q2 == false) {
        _q3 = false; _q4 = 0;
        _determinedRank = 0;
        _currentQuestion = _questions.length;
        return;
      }
      if (_currentQuestion == 2 && _q3 == false) {
        _q4 = 0;
        _determinedRank = 1;
        _currentQuestion = _questions.length;
        return;
      }

      if (_currentQuestion < _questions.length - 1) {
        _currentQuestion++;
      } else {
        _determinedRank = _determineRank();
        _currentQuestion = _questions.length; // show result
      }
    });
  }

  Future<void> _submitRank() async {
    setState(() => _isLoading = true);
    try {
      await ApiService.dio.post('/user-tasks/questionnaire', queryParameters: {
        'q1': _q1 ?? false,
        'q2': _q2 ?? false,
        'q3': _q3 ?? false,
        'q4': _q4 ?? 0,
      });

      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => TaskSelectionScreen(user: widget.user),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => TaskSelectionScreen(user: widget.user),
          ),
        );
      }
    }
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final showResult = _currentQuestion >= _questions.length;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        title: const Text('Your Prayer Journey',
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary)),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: showResult ? _buildResult() : _buildQuestion(),
        ),
      ),
    );
  }

  Widget _buildQuestion() {
    final q = _questions[_currentQuestion];
    final total = _questions.length;
    final current = _currentQuestion + 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Progress
        Row(
          children: [
            Text('Question $current of $total',
                style: const TextStyle(
                    fontSize: 13, color: AppColors.textSecondary)),
            const Spacer(),
            Text('${((current / total) * 100).round()}%',
                style: const TextStyle(
                    fontSize: 13,
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: current / total,
            backgroundColor: AppColors.border,
            valueColor: const AlwaysStoppedAnimation(AppColors.primary),
            minHeight: 6,
          ),
        ),
        const SizedBox(height: 40),

        // Question
        Container(
          width: 56, height: 56,
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Icon(Icons.mosque_rounded,
              color: AppColors.primary, size: 28),
        ),
        const SizedBox(height: 20),
        Text(q['question'],
            style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
                height: 1.3)),
        const SizedBox(height: 8),
        Text(q['subtitle'],
            style: const TextStyle(
                fontSize: 14, color: AppColors.textSecondary)),
        const SizedBox(height: 40),

        // Options
        ...List.generate(q['options'].length, (i) {
          final option = q['options'][i];
          final value = q['type'] == 'bool' ? (i == 1) : i;
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: GestureDetector(
              onTap: () => _answerQuestion(value),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(children: [
                  Container(
                    width: 36, height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Center(
                      child: Text(
                        String.fromCharCode(65 + i),
                        style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: AppColors.primary),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(option,
                        style: const TextStyle(
                            fontSize: 15,
                            color: AppColors.textPrimary)),
                  ),
                  const Icon(Icons.arrow_forward_ios_rounded,
                      size: 16, color: AppColors.textHint),
                ]),
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget _buildResult() {
    final rank = _determinedRank ?? 0;
    final rankName = _getRankName(rank);
    final rankDesc = _getRankDescription(rank);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Spacer(),
        Container(
          width: 100, height: 100,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.primary, AppColors.primaryDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(28),
          ),
          child: const Icon(Icons.star_rounded,
              color: Colors.white, size: 52),
        ),
        const SizedBox(height: 24),
        const Text('Your Rank',
            style: TextStyle(
                fontSize: 16, color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        Text(rankName,
            style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: AppColors.primary),
            textAlign: TextAlign.center),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Text(rankDesc,
              style: const TextStyle(
                  fontSize: 15, color: AppColors.textPrimary),
              textAlign: TextAlign.center),
        ),
        const SizedBox(height: 16),
        const Text(
          'You can retake this questionnaire anytime from your profile to update your rank.',
          style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const Spacer(),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _submitRank,
            child: _isLoading
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 2))
                : const Text('Continue — Choose Your Tasks'),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }
}
