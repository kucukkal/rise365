import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    switch (defaultTargetPlatform) {
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.android:
        return android;
      default:
        return ios;
    }
  }

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyAZ5aH-paXx-WUdBfkXIZOrvsCtwNDqG-Q',
    appId: '1:490823510657:ios:c63b8f5aa89da8ca38bb80',
    messagingSenderId: '490823510657',
    projectId: 'rise365-99977',
    storageBucket: 'rise365-99977.firebasestorage.app',
    iosBundleId: 'com.rise365.app',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyAZ5aH-paXx-WUdBfkXIZOrvsCtwNDqG-Q',
    appId: '1:490823510657:android:c63b8f5aa89da8ca38bb80',
    messagingSenderId: '490823510657',
    projectId: 'rise365-99977',
    storageBucket: 'rise365-99977.firebasestorage.app',
  );
}
