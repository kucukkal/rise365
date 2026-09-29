import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../core/services/api_service.dart';

class ExcelContentViewer extends StatefulWidget {
  final String taskId;
  final String taskTitle;

  /// Optional colors so the viewer matches its task bar.
  /// Leave null to keep the default app colors.
  final Color? accentColor; // borders, icons, arrows
  final Color? tintColor;   // panel background
  final Color? inkColor;    // title text

  const ExcelContentViewer({
    super.key,
    required this.taskId,
    required this.taskTitle,
    this.accentColor,
    this.tintColor,
    this.inkColor,
  });

  @override
  State<ExcelContentViewer> createState() => _ExcelContentViewerState();
}

class _ExcelContentViewerState extends State<ExcelContentViewer> {
  Color get _accent => widget.accentColor ?? AppColors.primary;
  Color get _ink => widget.inkColor ?? AppColors.primary;
  Color get _panelBg => widget.tintColor ?? AppColors.background;
  Color get _panelBorder =>
      widget.accentColor?.withOpacity(0.35) ?? AppColors.border;
  Color get _headerBg =>
      widget.accentColor?.withOpacity(0.14) ??
      AppColors.primary.withOpacity(0.06);

  String? _content;
  String? _information;
  int _rowNumber = 1;
  int _totalRows = 1;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) setState(() => _isLoading = true);
    try {
      final res = await ApiService.dio.get(
          '/content-tasks/today/${widget.taskId}');
      final data = res.data;
      if (mounted) setState(() {
        _content = data['content'];
        _information = data['information'];
        _rowNumber = data['row_number'] ?? 1;
        _totalRows = data['total_rows'] ?? 1;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = 'No content available';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator(
            color: _accent, strokeWidth: 2)),
      );
    }

    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Center(child: Text(_error!,
            style: const TextStyle(
                fontSize: 13, color: AppColors.textSecondary))),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: _panelBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _panelBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: _headerBg,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
            child: Row(children: [
              Icon(Icons.format_list_numbered_rounded,
                  color: _accent, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(widget.taskTitle,
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: _ink)),
              ),
              Text('Day $_rowNumber of $_totalRows',
                  style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.textSecondary)),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: _load,
                child: const Icon(Icons.refresh,
                    color: AppColors.textHint, size: 16),
              ),
            ]),
          ),

          // Content (Column A)
          if (_content != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                border: Border(
                    bottom: BorderSide(color: AppColors.border)),
              ),
              child: Text(
                _content!,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                  height: 1.5,
                ),
                textAlign: TextAlign.center,
                textDirection: TextDirection.rtl,
              ),
            ),

          // Information (Column B)
          if (_information != null && _information!.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.accent.withOpacity(0.04),
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(12),
                  bottomRight: Radius.circular(12),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline_rounded,
                      color: AppColors.accent, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _information!,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textSecondary,
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
