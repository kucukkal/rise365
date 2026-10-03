import 'package:flutter/foundation.dart';

/// Bumped whenever progress may have changed (e.g. switching tabs),
/// so screens kept alive in the background reload their numbers.
final ValueNotifier<int> progressRefresh = ValueNotifier<int>(0);
