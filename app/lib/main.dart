import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'firebase_options.dart';
import 'core/theme/app_theme.dart';
import 'core/services/api_service.dart';
import 'core/services/users_api.dart';
import 'core/services/notification_navigation.dart';
import 'features/home/screens/splash_screen.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  print('Background message: ${message.notification?.title}');
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    print('✅ Firebase initialized successfully');
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
    await _setupNotifications();
  } catch (e) {
    print('❌ Firebase init error: $e');
  }

  runApp(const ProviderScope(child: Rise365App()));
}

Future<void> _setupNotifications() async {
  final messaging = FirebaseMessaging.instance;

  // Request permission first
  final settings = await messaging.requestPermission(
    alert: true,
    badge: true,
    sound: true,
    provisional: false,
  );

  print('Permission status: ${settings.authorizationStatus}');

  if (settings.authorizationStatus == AuthorizationStatus.authorized ||
      settings.authorizationStatus == AuthorizationStatus.provisional) {

    // Wait for APNS token first (iOS requirement)
    try {
      final apnsToken = await messaging.getAPNSToken().timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          print('⚠️ APNS token timeout — continuing anyway');
          return null;
        },
      );
      print('APNS Token: $apnsToken');
    } catch (e) {
      print('APNS token error (non-fatal): $e');
    }

    // Now get FCM token
    try {
      final token = await messaging.getToken();
      print('🔥 FCM Token: ${token?.substring(0, 20)}...');
      if (token != null) {
        await _saveFcmToken(token);
      }
    } catch (e) {
      print('FCM token error: $e');
    }

    // Listen for token refresh
    messaging.onTokenRefresh.listen(_saveFcmToken);

    // Foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('Foreground message: ${message.notification?.title}');
    });

    // Handle notification tap when app is in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      print('Notification tapped: ${message.data}');
      _handleNotificationTap(message.data);
    });

    // Handle notification tap when app was terminated
    final initialMessage = await messaging.getInitialMessage();
    if (initialMessage != null) {
      _handleNotificationTap(initialMessage.data);
    }
  }
}

// Global navigator key for navigation from outside widget tree
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void _handleNotificationTap(Map<String, dynamic> data) {
  final type = data['type'] ?? '';
  final tab = data['tab'] ?? 'tasks';
  final frequency = data['frequency'] ?? 'daily';
  print('Notification tap: type=$type tab=$tab frequency=$frequency');

  int tabIndex = 0;
  if (tab == 'prayer' || type.contains('prayer')) {
    tabIndex = 1;
  }

  navigateToTab(tabIndex, frequency: frequency);
}

Future<void> _saveFcmToken(String token) async {
  print('💾 Saving FCM token...');
  try {
    final isLoggedIn = await ApiService.isLoggedIn();
    if (isLoggedIn) {
      await UsersApi.updateFcmToken(token);
      print('✅ FCM token saved to backend');
    } else {
      print('⚠️ Not logged in — token will be saved after login');
    }
  } catch (e) {
    print('❌ FCM token save error: $e');
  }
}

class Rise365App extends StatelessWidget {
  const Rise365App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rise365',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      navigatorKey: navigatorKey,
      home: const SplashScreen(),
    );
  }
}
