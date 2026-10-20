import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/services/progress_refresh.dart';

String _errorText(Object e, [String fallback = 'Something went wrong. Please try again.']) {
  if (e is DioException) {
    final data = e.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'];
  }
  return fallback;
}

void _toast(BuildContext context, String text, {bool error = false}) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
    content: Text(text),
    backgroundColor: error ? AppColors.error : AppColors.primary,
  ));
}

// ═════════════════════════════════════════════════════════════════════════════
// Circles tab
// ═════════════════════════════════════════════════════════════════════════════

class CirclesScreen extends StatefulWidget {
  const CirclesScreen({super.key});

  @override
  State<CirclesScreen> createState() => _CirclesScreenState();
}

class _CirclesScreenState extends State<CirclesScreen> {
  bool _loading = true;
  String? _error;
  List<dynamic> _circles = [];
  List<dynamic> _invitations = [];
  List<dynamic> _requests = [];
  bool _ownsCircle = false;
  bool _canJoinMore = true;
  int _maxCircles = 2;

  @override
  void initState() {
    super.initState();
    _load();
    progressRefresh.addListener(_onTabRefresh);
  }

  void _onTabRefresh() {
    if (mounted) _load();
  }

  @override
  void dispose() {
    progressRefresh.removeListener(_onTabRefresh);
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final res = await ApiService.dio.get('/circles/mine');
      final d = res.data;
      if (!mounted) return;
      setState(() {
        _circles = d['circles'] ?? [];
        _invitations = d['invitations'] ?? [];
        _requests = d['requests'] ?? [];
        _ownsCircle = d['owns_circle'] == true;
        _canJoinMore = d['can_join_more'] != false;
        _maxCircles = d['max_circles'] ?? 2;
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = "Couldn't load your circles.";
        _loading = false;
      });
    }
  }

  Future<void> _post(String path, {Map<String, dynamic>? data, String? success}) async {
    try {
      final res = await ApiService.dio.post(path, data: data);
      if (!mounted) return;
      _toast(context, success ?? (res.data['message'] ?? 'Done'));
      await _load();
    } catch (e) {
      if (mounted) _toast(context, _errorText(e), error: true);
    }
  }

  // ── dialogs ───────────────────────────────────────────────────────────────

  Future<void> _createCircle() async {
    final name = TextEditingController();
    final ok = await _formDialog(
      title: 'Create a circle',
      intro: 'Choose a name your family or friends will recognize. '
          'Names must be unique.',
      fields: [_Field(name, 'Circle name', 'e.g. Friday Brothers',
          capitalization: TextCapitalization.words, maxLength: 40)],
      action: 'Create',
    );
    if (ok != true || name.text.trim().isEmpty) return;
    await _post('/circles/create', data: {'name': name.text.trim()});
  }

  Future<void> _joinCircle() async {
    final circle = TextEditingController();
    final owner = TextEditingController();
    final ok = await _formDialog(
      title: 'Join a circle',
      intro: "Enter the circle's name and its owner's full name. "
          'The owner will be asked to approve your request.',
      fields: [
        _Field(circle, 'Circle name', 'e.g. Friday Brothers',
            capitalization: TextCapitalization.words, maxLength: 40),
        _Field(owner, "Owner's full name", 'e.g. Mustafa Kucukkal',
            capitalization: TextCapitalization.words, maxLength: 80),
      ],
      action: 'Send request',
    );
    if (ok != true) return;
    if (circle.text.trim().isEmpty || owner.text.trim().isEmpty) {
      _toast(context, 'Please enter both the circle name and the owner\'s name.', error: true);
      return;
    }
    await _post('/circles/join-request',
        data: {'circle_name': circle.text.trim(), 'owner_name': owner.text.trim()});
  }

  Future<void> _invite() async {
    final phone = TextEditingController();
    final ok = await _formDialog(
      title: 'Invite to your circle',
      intro: "Enter the person's phone number. They'll get an invitation "
          'they can accept or decline.',
      fields: [_Field(phone, 'Phone number', '(555) 000-0000',
          keyboard: TextInputType.phone, digitsOnly: true, maxLength: 11)],
      action: 'Send invitation',
    );
    if (ok != true || phone.text.trim().length < 10) {
      if (ok == true) _toast(context, 'Please enter a valid phone number.', error: true);
      return;
    }
    await _post('/circles/invite', data: {'phone': phone.text.trim()});
  }

  Future<bool?> _formDialog({
    required String title,
    required String intro,
    required List<_Field> fields,
    required String action,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(intro,
                  style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
              const SizedBox(height: 14),
              for (final f in fields) ...[
                TextField(
                  controller: f.controller,
                  textCapitalization: f.capitalization,
                  keyboardType: f.keyboard,
                  maxLength: f.maxLength,
                  autocorrect: false,
                  inputFormatters: f.digitsOnly
                      ? [FilteringTextInputFormatter.digitsOnly]
                      : null,
                  decoration: InputDecoration(
                    labelText: f.label,
                    hintText: f.hint,
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 10),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(action,
                  style: const TextStyle(fontWeight: FontWeight.w600))),
        ],
      ),
    );
  }

  // ── build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          color: AppColors.primary,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              const Text('Circles',
                  style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary)),
              const SizedBox(height: 4),
              const Text('Grow together with the people around you',
                  style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
              const SizedBox(height: 18),
              _buildActions(),
              const SizedBox(height: 20),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(
                      child: CircularProgressIndicator(
                          color: AppColors.primary, strokeWidth: 2)),
                )
              else if (_error != null)
                _InfoCard(
                  icon: Icons.cloud_off_rounded,
                  text: _error!,
                  actionLabel: 'Try again',
                  onAction: () {
                    setState(() => _loading = true);
                    _load();
                  },
                )
              else ...[
                if (_requests.isNotEmpty || _invitations.isNotEmpty) ...[
                  const _SectionTitle('Requests & invitations'),
                  for (final r in _requests)
                    _ActionCard(
                      icon: Icons.person_add_alt_1_rounded,
                      text: r['message'] ?? '',
                      positive: 'Approve',
                      negative: 'Decline',
                      onPositive: () => _post('/circles/requests/${r['id']}/approve'),
                      onNegative: () => _post('/circles/requests/${r['id']}/decline'),
                    ),
                  for (final i in _invitations)
                    _ActionCard(
                      icon: Icons.mail_outline_rounded,
                      text: i['message'] ?? '',
                      positive: 'Accept',
                      negative: 'Decline',
                      onPositive: () => _post('/circles/invitations/${i['id']}/accept'),
                      onNegative: () => _post('/circles/invitations/${i['id']}/decline'),
                    ),
                  const SizedBox(height: 16),
                ],
                _SectionTitle('My circles (${_circles.length}/$_maxCircles)'),
                if (_circles.isEmpty)
                  const _InfoCard(
                    icon: Icons.groups_2_outlined,
                    text: 'You are not in a circle yet. Create one for your family '
                        'or friends, or join a circle someone has created.',
                  )
                else
                  for (final c in _circles)
                    _CircleCard(
                      circle: c,
                      onTap: () async {
                        await Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => CircleDetailScreen(
                                  circleId: c['id'], circleName: c['name'])),
                        );
                        _load();
                      },
                    ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActions() {
    final canCreate = !_ownsCircle && _canJoinMore;
    return Column(children: [
      Row(children: [
        Expanded(
          child: _ActionButton(
            icon: Icons.add_circle_outline_rounded,
            label: 'Create Circle',
            enabled: canCreate,
            onTap: _createCircle,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _ActionButton(
            icon: Icons.login_rounded,
            label: 'Join Circle',
            enabled: _canJoinMore,
            onTap: _joinCircle,
          ),
        ),
      ]),
      if (_ownsCircle) ...[
        const SizedBox(height: 10),
        _ActionButton(
          icon: Icons.person_add_alt_1_rounded,
          label: 'Invite to Circle',
          enabled: true,
          onTap: _invite,
        ),
      ],
      if (!_loading && !_canJoinMore)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            "You're in $_maxCircles circles, the maximum. Leave one to join or create another.",
            style: const TextStyle(fontSize: 12, color: AppColors.textHint),
            textAlign: TextAlign.center,
          ),
        ),
    ]);
  }
}

class _Field {
  final TextEditingController controller;
  final String label;
  final String hint;
  final TextCapitalization capitalization;
  final TextInputType keyboard;
  final bool digitsOnly;
  final int maxLength;
  _Field(this.controller, this.label, this.hint,
      {this.capitalization = TextCapitalization.none,
      this.keyboard = TextInputType.text,
      this.digitsOnly = false,
      this.maxLength = 40});
}

// ═════════════════════════════════════════════════════════════════════════════
// Circle detail: members and their progress %
// ═════════════════════════════════════════════════════════════════════════════

class CircleDetailScreen extends StatefulWidget {
  final String circleId;
  final String circleName;
  const CircleDetailScreen(
      {super.key, required this.circleId, required this.circleName});

  @override
  State<CircleDetailScreen> createState() => _CircleDetailScreenState();
}

class _CircleDetailScreenState extends State<CircleDetailScreen> {
  bool _loading = true;
  String? _error;
  bool _isOwner = false;
  List<dynamic> _members = [];
  Map<String, dynamic>? _contest;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        ApiService.dio.get('/circles/${widget.circleId}'),
        ApiService.dio.get('/circles/${widget.circleId}/contests/active'),
      ]);
      if (!mounted) return;
      setState(() {
        _isOwner = results[0].data['is_owner'] == true;
        _members = results[0].data['members'] ?? [];
        _contest = results[1].data['contest'];
        _error = null;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _errorText(e, "Couldn't load this circle.");
        _loading = false;
      });
    }
  }

  Future<bool> _confirm(String title, String body, String action) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(action,
                  style: const TextStyle(
                      color: AppColors.error, fontWeight: FontWeight.w600))),
        ],
      ),
    );
    return ok == true;
  }

  // ── contest ───────────────────────────────────────────────────────────────

  Future<void> _startContest() async {
    final titleCtrl = TextEditingController();
    DateTime? startDt;
    DateTime? endDt;
    final minPctCtrl = TextEditingController();
    final minDaysCtrl = TextEditingController();

    Future<DateTime?> pickDateTime(BuildContext ctx, String label) async {
      final d = await showDatePicker(
        context: ctx,
        initialDate: DateTime.now().add(const Duration(minutes: 5)),
        firstDate: DateTime.now().subtract(const Duration(minutes: 1)),
        lastDate: DateTime.now().add(const Duration(days: 365)),
      );
      if (d == null) return null;
      final t = await showTimePicker(context: ctx, initialTime: TimeOfDay.now());
      if (t == null) return null;
      return DateTime(d.year, d.month, d.day, t.hour, t.minute);
    }

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setS) {
        return AlertDialog(
          title: const Text('Start a Contest'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(
                controller: titleCtrl,
                maxLength: 100,
                decoration: const InputDecoration(
                    labelText: 'Contest title', hintText: 'e.g. Ramadan Sprint',
                    counterText: ''),
              ),
              const SizedBox(height: 14),
              // Start date
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.play_circle_outline, color: AppColors.primary),
                title: Text(startDt == null
                    ? 'Set start date & time'
                    : 'Starts: ${_fmtDt(startDt!)}',
                    style: TextStyle(
                        fontSize: 14,
                        color: startDt == null
                            ? AppColors.textSecondary
                            : AppColors.textPrimary)),
                onTap: () async {
                  final dt = await pickDateTime(ctx, 'Start');
                  if (dt != null) setS(() => startDt = dt);
                },
              ),
              // End date
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.stop_circle_outlined, color: AppColors.error),
                title: Text(endDt == null
                    ? 'Set end date & time'
                    : 'Ends: ${_fmtDt(endDt!)}',
                    style: TextStyle(
                        fontSize: 14,
                        color: endDt == null
                            ? AppColors.textSecondary
                            : AppColors.textPrimary)),
                onTap: () async {
                  final dt = await pickDateTime(ctx, 'End');
                  if (dt != null) setS(() => endDt = dt);
                },
              ),
              const Divider(height: 24),
              const Text('Winning rules (optional)',
                  style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary)),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(
                  child: TextField(
                    controller: minPctCtrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                        labelText: 'Min daily %',
                        hintText: 'e.g. 80',
                        counterText: ''),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: minDaysCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                        labelText: 'Min days',
                        hintText: 'e.g. 6',
                        counterText: ''),
                  ),
                ),
              ]),
              const SizedBox(height: 8),
              const Text(
                'Leave both blank to rank by total progress sum.',
                style: TextStyle(fontSize: 11, color: AppColors.textHint),
              ),
            ]),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel')),
            TextButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Create',
                    style: TextStyle(fontWeight: FontWeight.w600))),
          ],
        );
      }),
    );

    if (ok != true) return;
    if (titleCtrl.text.trim().isEmpty) {
      _toast(context, 'Please enter a contest title.', error: true);
      return;
    }
    if (startDt == null || endDt == null) {
      _toast(context, 'Please set both start and end date/time.', error: true);
      return;
    }
    if (!endDt!.isAfter(startDt!)) {
      _toast(context, 'End must be after start.', error: true);
      return;
    }

    final body = <String, dynamic>{
      'title': titleCtrl.text.trim(),
      'start_at': startDt!.toUtc().toIso8601String(),
      'end_at': endDt!.toUtc().toIso8601String(),
    };
    final pct = double.tryParse(minPctCtrl.text.trim());
    final days = int.tryParse(minDaysCtrl.text.trim());
    if (pct != null) body['min_progress_pct'] = pct;
    if (days != null) body['min_days'] = days;

    try {
      await ApiService.dio.post(
          '/circles/${widget.circleId}/contests', data: body);
      if (mounted) _toast(context, 'Contest started! 🏆');
      _load();
    } catch (e) {
      if (mounted) _toast(context, _errorText(e), error: true);
    }
  }

  Future<void> _cancelContest() async {
    final ok = await _confirm(
      'Cancel contest?',
      'The contest will be cancelled and members notified.',
      'Cancel contest',
    );
    if (!ok) return;
    try {
      await ApiService.dio
          .delete('/circles/${widget.circleId}/contests/active');
      if (mounted) _toast(context, 'Contest cancelled');
      _load();
    } catch (e) {
      if (mounted) _toast(context, _errorText(e), error: true);
    }
  }

  String _fmtDt(DateTime dt) {
    final m = dt.month.toString().padLeft(2, '0');
    final d = dt.day.toString().padLeft(2, '0');
    final h = dt.hour.toString().padLeft(2, '0');
    final min = dt.minute.toString().padLeft(2, '0');
    return '${dt.year}/$m/$d  $h:$min';
  }

  String _countdown(String endAtIso) {
    try {
      final end = DateTime.parse(endAtIso).toLocal();
      final diff = end.difference(DateTime.now());
      if (diff.isNegative) return 'Ended';
      if (diff.inDays > 0) return '${diff.inDays}d ${diff.inHours % 24}h left';
      if (diff.inHours > 0) return '${diff.inHours}h ${diff.inMinutes % 60}m left';
      return '${diff.inMinutes}m left';
    } catch (_) {
      return '';
    }
  }

  Widget _buildContestSection() {
    final contest = _contest;

    if (contest == null) {
      if (!_isOwner) return const SizedBox.shrink();
      // Owner: no contest — show start button
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const _SectionTitle('Contest'),
        OutlinedButton.icon(
          onPressed: _startContest,
          icon: const Icon(Icons.emoji_events_outlined, size: 18),
          label: const Text('Start a Contest'),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primary,
            side: const BorderSide(color: AppColors.primary),
            padding: const EdgeInsets.symmetric(vertical: 12),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
          ),
        ),
        const SizedBox(height: 24),
      ]);
    }

    final ranked = (contest['ranked'] as List?) ?? [];
    final mentions = (contest['honorable_mentions'] as List?) ?? [];
    final hasWinner = contest['has_winner'] == true;
    final status = contest['status'] ?? 'active';
    final isActive = status == 'active';
    final countdown = isActive ? _countdown(contest['end_at'] ?? '') : 'Ended';
    final minPct = contest['min_progress_pct'];
    final minDays = contest['min_days'];

    // Build rule description
    String ruleDesc = '';
    if (minPct != null && minDays != null) {
      ruleDesc = 'Goal: ${minPct.round()}%+ daily for ${minDays}+ days';
    } else if (minDays != null) {
      ruleDesc = 'Goal: active for $minDays+ days';
    } else {
      ruleDesc = 'Goal: highest total progress';
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Expanded(child: _SectionTitle('Contest')),
        if (_isOwner && isActive)
          TextButton(
            onPressed: _startContest,
            style: TextButton.styleFrom(padding: EdgeInsets.zero),
            child: const Text('+ New',
                style: TextStyle(color: AppColors.textHint, fontSize: 12)),
          ),
      ]),

      Container(
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
              color: isActive
                  ? AppColors.primary.withOpacity(0.5)
                  : AppColors.border),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            decoration: BoxDecoration(
              color: isActive
                  ? AppColors.primary.withOpacity(0.08)
                  : AppColors.surface,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(15)),
            ),
            child: Row(children: [
              const Text('🏆', style: TextStyle(fontSize: 20)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(contest['title'] ?? '',
                          style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary)),
                      const SizedBox(height: 2),
                      Text(ruleDesc,
                          style: const TextStyle(
                              fontSize: 11, color: AppColors.textSecondary)),
                    ]),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isActive
                      ? AppColors.primary.withOpacity(0.15)
                      : AppColors.border,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  isActive ? countdown : 'Ended',
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: isActive
                          ? AppColors.primary
                          : AppColors.textSecondary),
                ),
              ),
            ]),
          ),

          const Divider(height: 1),

          // Leaderboard or no-winner section
          if (!hasWinner && mentions.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.amber.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                        border:
                            Border.all(color: Colors.amber.withOpacity(0.4)),
                      ),
                      child: const Text(
                        '🏁 No Official Winner · Contest goal not reached',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Colors.amber),
                      ),
                    ),
                    const SizedBox(height: 10),
                    const Text('Honorable Mentions',
                        style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary)),
                    const SizedBox(height: 6),
                    for (final m in mentions)
                      _ContestMedalRow(
                          entry: m, isHonorable: true, minPct: minPct),
                  ]),
            ),
          ] else if (ranked.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
              child: Column(children: [
                for (final m in ranked)
                  _ContestMedalRow(
                      entry: m, isHonorable: false, minPct: minPct),
              ]),
            ),
          ],

          // Owner controls
          if (_isOwner && isActive)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 12),
              child: TextButton(
                onPressed: _cancelContest,
                child: const Text('Cancel contest',
                    style: TextStyle(color: AppColors.error, fontSize: 12)),
              ),
            )
          else
            const SizedBox(height: 12),
        ]),
      ),
      const SizedBox(height: 24),

      // Show "Start Contest" button for owner after a completed contest
      if (_isOwner && !isActive)
        Padding(
          padding: const EdgeInsets.only(bottom: 24),
          child: OutlinedButton.icon(
            onPressed: _startContest,
            icon: const Icon(Icons.emoji_events_outlined, size: 18),
            label: const Text('Start New Contest'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.primary,
              side: const BorderSide(color: AppColors.primary),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
    ]);
  }

  Future<void> _removeMember(Map m) async {
    if (!await _confirm('Remove ${m['name']}?',
        "${m['name']} will be removed from ${widget.circleName}.", 'Remove')) return;
    try {
      await ApiService.dio.delete('/circles/${widget.circleId}/members/${m['user_id']}');
      if (mounted) _toast(context, '${m['name']} was removed');
      _load();
    } catch (e) {
      if (mounted) _toast(context, _errorText(e), error: true);
    }
  }

  Future<void> _leaveOrDelete() async {
    final deleting = _isOwner;
    final ok = await _confirm(
      deleting ? 'Delete this circle?' : 'Leave this circle?',
      deleting
          ? 'This deletes ${widget.circleName} for everyone. Members will be notified.'
          : "You'll leave ${widget.circleName}. You can ask to join again later.",
      deleting ? 'Delete' : 'Leave',
    );
    if (!ok) return;
    try {
      if (deleting) {
        await ApiService.dio.delete('/circles/${widget.circleId}');
      } else {
        await ApiService.dio.post('/circles/${widget.circleId}/leave');
      }
      if (!mounted) return;
      _toast(context, deleting ? 'Circle deleted' : 'You left ${widget.circleName}');
      Navigator.pop(context);
    } catch (e) {
      if (mounted) _toast(context, _errorText(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final avg = _members.isEmpty
        ? 0
        : (_members.map((m) => (m['progress'] ?? 0) as num).reduce((a, b) => a + b) /
                _members.length)
            .round();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        foregroundColor: AppColors.textPrimary,
        title: Text(widget.circleName,
            style: const TextStyle(fontWeight: FontWeight.w600)),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        color: AppColors.primary,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(
                    child: CircularProgressIndicator(
                        color: AppColors.primary, strokeWidth: 2)),
              )
            else if (_error != null)
              _InfoCard(icon: Icons.error_outline_rounded, text: _error!)
            else ...[
              // Circle summary
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(children: [
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Together this period',
                              style: TextStyle(color: Colors.white, fontSize: 13)),
                          const SizedBox(height: 4),
                          Text('$avg%',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 30,
                                  fontWeight: FontWeight.bold)),
                        ]),
                  ),
                  Text(
                      '${_members.length} member${_members.length == 1 ? '' : 's'}',
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.85), fontSize: 13)),
                ]),
              ),
              const SizedBox(height: 18),
              _buildContestSection(),
              const _SectionTitle('Members'),
              for (var i = 0; i < _members.length; i++)
                _MemberRow(
                  rank: i + 1,
                  member: _members[i],
                  canRemove: _isOwner && _members[i]['is_me'] != true,
                  onRemove: () => _removeMember(_members[i]),
                ),
              const SizedBox(height: 24),
              Center(
                child: TextButton.icon(
                  onPressed: _leaveOrDelete,
                  icon: Icon(
                      _isOwner ? Icons.delete_outline : Icons.logout_rounded,
                      color: AppColors.error,
                      size: 18),
                  label: Text(_isOwner ? 'Delete circle' : 'Leave circle',
                      style: const TextStyle(color: AppColors.error)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// Small widgets
// ═════════════════════════════════════════════════════════════════════════════

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Text(text,
            style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary)),
      );
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool enabled;
  final VoidCallback onTap;
  const _ActionButton(
      {required this.icon,
      required this.label,
      required this.enabled,
      required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: enabled ? 1 : 0.45,
      child: Material(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: enabled ? onTap : null,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.primary.withOpacity(0.35)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, color: AppColors.primary, size: 20),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(label,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                          fontSize: 14)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CircleCard extends StatelessWidget {
  final Map circle;
  final VoidCallback onTap;
  const _CircleCard({required this.circle, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isOwner = circle['is_owner'] == true;
    final count = circle['member_count'] ?? 1;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.groups_2_rounded,
                    color: AppColors.primary, size: 26),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Flexible(
                        child: Text(circle['name'] ?? '',
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary)),
                      ),
                      if (isOwner) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text('Owner',
                              style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.primary)),
                        ),
                      ],
                    ]),
                    const SizedBox(height: 3),
                    Text(
                      isOwner
                          ? '$count member${count == 1 ? '' : 's'}'
                          : 'by ${circle['owner_name'] ?? ''} · $count member${count == 1 ? '' : 's'}',
                      style: const TextStyle(
                          fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: AppColors.textHint),
            ]),
          ),
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String text;
  final String positive;
  final String negative;
  final VoidCallback onPositive;
  final VoidCallback onNegative;
  const _ActionCard(
      {required this.icon,
      required this.text,
      required this.positive,
      required this.negative,
      required this.onPositive,
      required this.onNegative});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.primary.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(icon, color: AppColors.primary, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(text,
                  style: const TextStyle(
                      fontSize: 14, color: AppColors.textPrimary, height: 1.4)),
            ),
          ]),
          const SizedBox(height: 10),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(
                onPressed: onNegative,
                child: Text(negative,
                    style: const TextStyle(color: AppColors.textSecondary))),
            const SizedBox(width: 6),
            ElevatedButton(
              onPressed: onPositive,
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(0, 38),
                padding: const EdgeInsets.symmetric(horizontal: 18),
              ),
              child: Text(positive),
            ),
          ]),
        ],
      ),
    );
  }
}

class _MemberRow extends StatelessWidget {
  final int rank;
  final Map member;
  final bool canRemove;
  final VoidCallback onRemove;
  const _MemberRow(
      {required this.rank,
      required this.member,
      required this.canRemove,
      required this.onRemove});

  @override
  Widget build(BuildContext context) {
    final pct = ((member['progress'] ?? 0) as num).clamp(0, 100).toDouble();
    final isMe = member['is_me'] == true;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
      decoration: BoxDecoration(
        color: isMe ? AppColors.primary.withOpacity(0.06) : AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
            color: isMe ? AppColors.primary.withOpacity(0.35) : AppColors.border),
      ),
      child: Row(children: [
        SizedBox(
          width: 24,
          child: Text('$rank',
              style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textHint)),
        ),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Flexible(
                  child: Text(
                    isMe ? '${member['name']} (you)' : (member['name'] ?? ''),
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary),
                  ),
                ),
                if (member['is_owner'] == true) ...[
                  const SizedBox(width: 6),
                  const Icon(Icons.star_rounded,
                      size: 15, color: AppColors.accent),
                ],
              ]),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: pct / 100,
                  minHeight: 6,
                  backgroundColor: AppColors.border,
                  valueColor:
                      const AlwaysStoppedAnimation<Color>(AppColors.primary),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        Text('${pct.round()}%',
            style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: AppColors.primary)),
        if (canRemove)
          IconButton(
            tooltip: 'Remove',
            onPressed: onRemove,
            icon: const Icon(Icons.person_remove_alt_1_outlined,
                size: 20, color: AppColors.textHint),
          )
        else
          const SizedBox(width: 12),
      ]),
    );
  }
}

class _ContestMedalRow extends StatelessWidget {
  final Map entry;
  final bool isHonorable;
  final dynamic minPct; // nullable double

  const _ContestMedalRow(
      {required this.entry,
      required this.isHonorable,
      required this.minPct});

  @override
  Widget build(BuildContext context) {
    final rank = entry['rank'] ?? 0;
    final medal = entry['medal'] ?? '';
    final name = entry['name'] ?? '';
    final sumPct = ((entry['sum_pct'] ?? 0) as num).toDouble();
    final qualDays = (entry['qualifying_days'] ?? 0) as int;
    final isAchiever = entry['is_achiever'] == true;

    final medals = {1: '🥇', 2: '🥈', 3: '🥉'};
    final displayMedal = isHonorable ? (medals[rank] ?? '') : medal;

    Color? bgColor;
    if (!isHonorable) {
      if (rank == 1 && isAchiever) bgColor = const Color(0xFFFFF8E1); // gold tint
      if (rank == 2 && isAchiever) bgColor = const Color(0xFFF5F5F5); // silver tint
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: bgColor ?? Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isHonorable
              ? Colors.amber.withOpacity(0.3)
              : (isAchiever
                  ? AppColors.primary.withOpacity(0.2)
                  : AppColors.border.withOpacity(0.5)),
        ),
      ),
      child: Row(children: [
        SizedBox(
          width: 30,
          child: Text(
            displayMedal.isNotEmpty ? displayMedal : '$rank',
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: displayMedal.isNotEmpty ? 18 : 13,
                fontWeight: FontWeight.w600,
                color: AppColors.textHint),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    fontSize: 13,
                    fontWeight:
                        isAchiever ? FontWeight.w700 : FontWeight.w500,
                    color: AppColors.textPrimary)),
            if (minPct != null && qualDays > 0)
              Text('$qualDays qualifying day${qualDays == 1 ? '' : 's'}',
                  style: const TextStyle(
                      fontSize: 11, color: AppColors.textSecondary)),
          ]),
        ),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('${sumPct.toStringAsFixed(0)}%',
              style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: isAchiever ? AppColors.primary : AppColors.textSecondary)),
          if (isHonorable)
            const Text('honorable mention',
                style: TextStyle(fontSize: 9, color: Colors.amber)),
        ]),
      ]),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final IconData icon;
  final String text;
  final String? actionLabel;
  final VoidCallback? onAction;
  const _InfoCard(
      {required this.icon, required this.text, this.actionLabel, this.onAction});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(children: [
        Icon(icon, size: 36, color: AppColors.textHint),
        const SizedBox(height: 10),
        Text(text,
            textAlign: TextAlign.center,
            style: const TextStyle(
                fontSize: 13, color: AppColors.textSecondary, height: 1.5)),
        if (actionLabel != null) ...[
          const SizedBox(height: 10),
          TextButton(onPressed: onAction, child: Text(actionLabel!)),
        ],
      ]),
    );
  }
}
