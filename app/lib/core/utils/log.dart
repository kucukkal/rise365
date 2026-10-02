import 'package:flutter/foundation.dart';

/// Prints only in debug builds (flutter run). Silent in TestFlight/App Store.
void devLog(Object? message) {
  if (kDebugMode) debugPrint('$message');
}
