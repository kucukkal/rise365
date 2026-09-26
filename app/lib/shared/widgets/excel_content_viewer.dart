import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../core/services/api_service.dart';

class ExcelContentViewer extends StatefulWidget {
  final String taskId;
  final String taskTitle;

  const ExcelContentViewer({
    super.key,
    required this.taskId,
    required this.taskTitle,
  });

  @override
  State<ExcelContentViewer> createState() => _ExcelContentViewerState();
}

class _ExcelContentViewerState extends State<ExcelContentViewer> {
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
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator(
            color: AppColors.primary, strokeWidth: 2)),
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
        color: AppColors.background,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.06),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
            child: Row(children: [
              const Icon(Icons.format_list_numbered_rounded,
                  color: AppColors.primary, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(widget.taskTitle,
                    style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primary)),
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
