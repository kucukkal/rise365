import 'package:purchases_flutter/purchases_flutter.dart';
import '../utils/log.dart';

/// Wraps RevenueCat for subscription management.
///
/// Setup steps:
///   1. Create a RevenueCat project at app.revenuecat.com
///   2. Add your iOS app and paste the API key below
///   3. In App Store Connect, create an Auto-Renewable Subscription:
///        Product ID: com.rise365.yearly    Price: $5.99/yr
///   4. In RevenueCat dashboard → Products → add that product ID
///   5. Create an Offering called "default" with an Annual package
///   6. Create an Entitlement called "premium" and attach the product
class SubscriptionService {
  // ── Replace with your actual RevenueCat iOS API key ──────────────────────
  static const String _rcApiKey = 'test_ftFnDcvzfrdSpOiMrUNgCLZdsda';

  static const String _entitlement = 'rise365_pro';

  /// Call once in main() before runApp.
  static Future<void> init() async {
    await Purchases.setLogLevel(LogLevel.debug);
    final config = PurchasesConfiguration(_rcApiKey);
    await Purchases.configure(config);
    devLog('✅ RevenueCat initialized');
  }

  /// Link RevenueCat to the signed-in user so their subscription follows them
  /// across devices. Call after a successful login/profile fetch.
  static Future<void> identifyUser(String userId) async {
    try {
      await Purchases.logIn(userId);
      devLog('✅ RevenueCat user: $userId');
    } catch (e) {
      devLog('RevenueCat identify error (non-fatal): $e');
    }
  }

  /// Returns true if the current user has an active "premium" entitlement.
  static Future<bool> isActive() async {
    try {
      final info = await Purchases.getCustomerInfo();
      final active = info.entitlements.active.containsKey(_entitlement);
      devLog('Subscription active: $active');
      return active;
    } catch (e) {
      devLog('Subscription check error (defaulting false): $e');
      return false;
    }
  }

  /// Fetches the yearly package price string, e.g. "$5.99".
  /// Returns null if offerings haven't loaded yet.
  static Future<String?> yearlyPriceString() async {
    try {
      final offerings = await Purchases.getOfferings();
      final pkg = offerings.current?.annual ??
          offerings.current?.availablePackages.firstOrNull;
      return pkg?.storeProduct.priceString;
    } catch (e) {
      devLog('Offerings error: $e');
      return null;
    }
  }

  /// Initiates the in-app purchase flow. Returns true on success.
  static Future<bool> purchase() async {
    try {
      final offerings = await Purchases.getOfferings();
      final pkg = offerings.current?.annual ??
          offerings.current?.availablePackages.firstOrNull;
      if (pkg == null) {
        devLog('No package found in current offering');
        return false;
      }
      await Purchases.purchasePackage(pkg);
      return await isActive();
    } on PurchasesErrorCode catch (e) {
      if (e == PurchasesErrorCode.purchaseCancelledError) {
        devLog('User cancelled purchase');
      } else {
        devLog('Purchase error: $e');
      }
      return false;
    } catch (e) {
      devLog('Purchase unexpected error: $e');
      return false;
    }
  }

  /// Restores previous purchases. Returns true if the user is now active.
  static Future<bool> restore() async {
    try {
      final info = await Purchases.restorePurchases();
      final active = info.entitlements.active.containsKey(_entitlement);
      devLog('Restore result: $active');
      return active;
    } catch (e) {
      devLog('Restore error: $e');
      return false;
    }
  }

  /// Call on logout to un-link the RevenueCat identity.
  static Future<void> logout() async {
    try {
      await Purchases.logOut();
    } catch (e) {
      devLog('RevenueCat logout error: $e');
    }
  }
}
