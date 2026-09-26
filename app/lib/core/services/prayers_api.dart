import 'api_service.dart';

class PrayersApi {
  static Future<Map<String, dynamic>> getTodayPrayers({
    String city = 'Herndon',
    String country = 'US',
  }) async {
    final response = await ApiService.dio.get(
      '/prayers/today',
      queryParameters: {'city': city, 'country': country},
    );
    return response.data;
  }

  static Future<Map<String, dynamic>> completePrayer(String prayerName) async {
    final response = await ApiService.dio.post('/prayers/complete', data: {
      'prayer_name': prayerName,
    });
    return response.data;
  }
}