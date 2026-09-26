import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../core/services/api_service.dart';

class PdfPageViewer extends StatefulWidget {
  final String taskId;
  final String taskTitle;

  const PdfPageViewer({
    super.key,
    required this.taskId,
    required this.taskTitle,
  });

  @override
  State<PdfPageViewer> createState() => _PdfPageViewerState();
}

class _PdfPageViewerState extends State<PdfPageViewer> {
  List<dynamic> _images = [];
  bool _isLoading = true;
  String? _error;
  String _todayPages = '';
  String _pdfTitle = '';
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _loadPages();
  }

  Future<void> _loadPages() async {
    if (mounted) setState(() => _isLoading = true);
    try {
      final response = await ApiService.dio.get(
        '/content-tasks/today/${widget.taskId}',
        queryParameters: {'as_images': true},
      );
      final data = response.data;
      if (mounted) setState(() {
        _images = data['images'] ?? [];
        _todayPages = data['today_pages'] ?? '';
        _pdfTitle = data['pdf_title'] ?? '';
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = 'No PDF content available for your level';
        _isLoading = false;
      });
    }
  }

  Uint8List _decodeBase64Image(String dataUri) {
    final base64Str = dataUri.contains(',')
        ? dataUri.split(',').last
        : dataUri;
    return base64Decode(base64Str);
  }

  @override
  Widget build(BuildContext context) {
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
              const Icon(Icons.menu_book_rounded,
                  color: AppColors.primary, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _pdfTitle.isEmpty ? widget.taskTitle : _pdfTitle,
                      style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppColors.primary),
                    ),
                    if (_todayPages.isNotEmpty)
                      Text('Today: pages $_todayPages',
                          style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textSecondary)),
                  ],
                ),
              ),
              // Page navigation
              if (_images.length > 1) ...[
                GestureDetector(
                  onTap: _currentPage > 0
                      ? () { if (mounted) setState(() => _currentPage--); }
                      : null,
                  child: Icon(Icons.chevron_left,
                      color: _currentPage > 0
                          ? AppColors.primary
                          : AppColors.textHint,
                      size: 24),
                ),
                Text('${_currentPage + 1}/${_images.length}',
                    style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary)),
                GestureDetector(
                  onTap: _currentPage < _images.length - 1
                      ? () { if (mounted) setState(() => _currentPage++); }
                      : null,
                  child: Icon(Icons.chevron_right,
                      color: _currentPage < _images.length - 1
                          ? AppColors.primary
                          : AppColors.textHint,
                      size: 24),
                ),
              ],
              // Refresh button
              GestureDetector(
                onTap: _loadPages,
                child: const Icon(Icons.refresh,
                    color: AppColors.textHint, size: 18),
              ),
            ]),
          ),

          // Content
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(
                child: CircularProgressIndicator(
                    color: AppColors.primary, strokeWidth: 2)),
            )
          else if (_error != null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Column(children: [
                  const Icon(Icons.picture_as_pdf_outlined,
                      color: AppColors.textHint, size: 32),
                  const SizedBox(height: 8),
                  Text(_error!,
                      style: const TextStyle(
                          fontSize: 13,
                          color: AppColors.textSecondary),
                      textAlign: TextAlign.center),
                ]),
              ),
            )
          else if (_images.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(
                child: Text('No pages available',
                    style: TextStyle(
                        fontSize: 13,
                        color: AppColors.textSecondary)),
              ),
            )
          else
            ClipRRect(
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(12),
                bottomRight: Radius.circular(12),
              ),
              child: Image.memory(
                _decodeBase64Image(
                    _images[_currentPage]['data'].toString()),
                fit: BoxFit.fitWidth,
                width: double.infinity,
                gaplessPlayback: true,
                errorBuilder: (_, e, __) => Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text('Error loading page: $e',
                      style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.error)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
