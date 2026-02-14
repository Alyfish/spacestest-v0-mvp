import 'package:flutter_test/flutter_test.dart';
import 'package:spaces/models/shop_product.dart';

void main() {
  group('ShopProduct.fromJson — snake_case backend handling', () {
    test('parses backend-style product with snake_case keys', () {
      final json = {
        'id': 'prod-1',
        'name': 'Modern Nightstand',
        'description': 'A sleek bedside table',
        'price': 149.99,
        'store': 'IKEA',
        'image_url': 'https://example.com/nightstand.jpg',
        'retailer_logo_url': 'https://example.com/ikea-logo.png',
        'color': 'Oak',
        'category': 'Furniture',
      };
      final product = ShopProduct.fromJson(json);
      expect(product.id, 'prod-1');
      expect(product.name, 'Modern Nightstand');
      expect(product.price, 149.99);
      expect(product.retailerName, 'IKEA');
      expect(product.imageUrl, 'https://example.com/nightstand.jpg');
      expect(product.retailerLogoUrl, 'https://example.com/ikea-logo.png');
    });

    test('parses camelCase keys (legacy format)', () {
      final json = {
        'id': 'prod-2',
        'name': 'Floor Lamp',
        'description': 'Warm LED lamp',
        'price': 79.00,
        'retailerName': 'West Elm',
        'imageUrl': 'https://example.com/lamp.jpg',
        'retailerLogoUrl': 'https://example.com/westelm-logo.png',
      };
      final product = ShopProduct.fromJson(json);
      expect(product.retailerName, 'West Elm');
      expect(product.imageUrl, 'https://example.com/lamp.jpg');
    });

    test('defaults retailerName to Unknown when missing', () {
      final json = {
        'id': 'prod-3',
        'name': 'Throw Pillow',
        'price': 29.99,
      };
      final product = ShopProduct.fromJson(json);
      expect(product.retailerName, 'Unknown');
    });

    test('defaults imageUrl to empty string when missing', () {
      final json = {
        'id': 'prod-4',
        'name': 'Rug',
        'price': 199.00,
      };
      final product = ShopProduct.fromJson(json);
      expect(product.imageUrl, '');
    });

    test('handles integer price cast to double', () {
      final json = {
        'id': 'prod-5',
        'name': 'Shelf',
        'price': 50, // int, not double
      };
      final product = ShopProduct.fromJson(json);
      expect(product.price, 50.0);
    });
  });

  group('ProductHotspot.fromJson — snake_case handling', () {
    test('parses item_type from snake_case', () {
      final json = {
        'id': 'hs-1',
        'x': 0.3,
        'y': 0.7,
        'item_type': 'sofa',
        'label': 'Modern Sofa',
      };
      final hotspot = ProductHotspot.fromJson(json);
      expect(hotspot.itemType, 'sofa');
      expect(hotspot.x, 0.3);
      expect(hotspot.y, 0.7);
    });

    test('parses furniture_type fallback', () {
      final json = {
        'id': 'hs-2',
        'x': 0.5,
        'y': 0.5,
        'furniture_type': 'lamp',
      };
      final hotspot = ProductHotspot.fromJson(json);
      expect(hotspot.itemType, 'lamp');
    });

    test('defaults itemType to "item" when all keys missing', () {
      final json = {
        'id': 'hs-3',
        'x': 0.1,
        'y': 0.9,
      };
      final hotspot = ProductHotspot.fromJson(json);
      expect(hotspot.itemType, 'item');
    });

    test('defaults label to "Product" when missing', () {
      final json = {
        'id': 'hs-4',
        'x': 0.0,
        'y': 1.0,
      };
      final hotspot = ProductHotspot.fromJson(json);
      expect(hotspot.label, 'Product');
    });
  });

  group('ShopProduct equality & toString', () {
    test('two products with same id are equal', () {
      final p1 = ShopProduct(
        id: 'eq-1',
        name: 'A',
        description: 'a',
        price: 10,
        retailerName: 'Store',
        imageUrl: 'url',
      );
      final p2 = ShopProduct(
        id: 'eq-1',
        name: 'B',
        description: 'b',
        price: 20,
        retailerName: 'Other',
        imageUrl: 'url2',
      );
      expect(p1, equals(p2));
      expect(p1.hashCode, p2.hashCode);
    });

    test('toString includes name and price', () {
      final p = ShopProduct(
        id: 'ts-1',
        name: 'Vase',
        description: '',
        price: 35.0,
        retailerName: 'Target',
        imageUrl: '',
      );
      expect(p.toString(), contains('Vase'));
      expect(p.toString(), contains('35.0'));
    });
  });

  group('ShopProduct.copyWith', () {
    test('copies with new price', () {
      final original = ShopProduct(
        id: 'cw-1',
        name: 'Chair',
        description: 'Comfy',
        price: 100,
        retailerName: 'IKEA',
        imageUrl: 'url',
      );
      final copied = original.copyWith(price: 89.99);
      expect(copied.price, 89.99);
      expect(copied.name, 'Chair'); // unchanged
      expect(copied.id, 'cw-1'); // unchanged
    });
  });
}
