/// Model for a product in the shopping/product selection screens
class ShopProduct {
  final String id;
  final String name;
  final String description;
  final double price;
  final String? displayPrice;
  final String retailerName;
  final String? retailerLogoUrl;
  final String imageUrl;
  final String? productUrl;
  final String? color;
  final String? category;

  const ShopProduct({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    this.displayPrice,
    required this.retailerName,
    this.retailerLogoUrl,
    required this.imageUrl,
    this.productUrl,
    this.color,
    this.category,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'price': price,
      'displayPrice': displayPrice,
      'retailerName': retailerName,
      'retailerLogoUrl': retailerLogoUrl,
      'imageUrl': imageUrl,
      'productUrl': productUrl,
      'color': color,
      'category': category,
    };
  }

  factory ShopProduct.fromJson(Map<String, dynamic> json) {
    final parsedPrice = _parseNumericPrice(
      json['price'],
      json['price_str'] ?? json['priceStr'],
    );
    final parsedDisplayPrice = _normalizeDisplayPrice(
      json['displayPrice'] ?? json['price_display'] ?? json['price_str'],
    );

    return ShopProduct(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      price: parsedPrice,
      displayPrice: parsedDisplayPrice,
      retailerName:
          json['retailerName'] as String? ??
          json['store'] as String? ??
          'Unknown',
      retailerLogoUrl:
          json['retailerLogoUrl'] as String? ??
          json['retailer_logo_url'] as String?,
      imageUrl:
          json['imageUrl'] as String? ?? json['image_url'] as String? ?? '',
      productUrl:
          json['productUrl'] as String? ??
          json['url'] as String? ??
          json['link'] as String?,
      color: json['color'] as String?,
      category: json['category'] as String?,
    );
  }

  ShopProduct copyWith({
    String? id,
    String? name,
    String? description,
    double? price,
    String? displayPrice,
    String? retailerName,
    String? retailerLogoUrl,
    String? imageUrl,
    String? productUrl,
    String? color,
    String? category,
  }) {
    return ShopProduct(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      price: price ?? this.price,
      displayPrice: displayPrice ?? this.displayPrice,
      retailerName: retailerName ?? this.retailerName,
      retailerLogoUrl: retailerLogoUrl ?? this.retailerLogoUrl,
      imageUrl: imageUrl ?? this.imageUrl,
      productUrl: productUrl ?? this.productUrl,
      color: color ?? this.color,
      category: category ?? this.category,
    );
  }

  @override
  String toString() {
    return 'ShopProduct(id: $id, name: $name, price: $price, retailer: $retailerName)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is ShopProduct && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  static double _parseNumericPrice(dynamic rawPrice, dynamic rawPriceStr) {
    if (rawPrice is num) {
      return rawPrice.toDouble();
    }
    if (rawPrice is String) {
      final parsed = double.tryParse(rawPrice.replaceAll(',', '').trim());
      if (parsed != null) return parsed;
    }

    final priceText = rawPriceStr?.toString().trim() ?? '';
    if (priceText.isEmpty) return 0.0;
    final match = RegExp(
      r'(\d+(?:\.\d+)?)',
    ).firstMatch(priceText.replaceAll(',', ''));
    if (match == null) return 0.0;
    return double.tryParse(match.group(1) ?? '') ?? 0.0;
  }

  static String? _normalizeDisplayPrice(dynamic rawValue) {
    final text = rawValue?.toString().trim() ?? '';
    if (text.isEmpty) return null;
    return text;
  }
}

/// Model for a hotspot/marker on the generated dream space image
class ProductHotspot {
  final String id;
  final double x; // Position as percentage (0-1)
  final double y; // Position as percentage (0-1)
  final String itemType; // 'couch', 'lamp', 'vase', etc.
  final String label;

  // Optional marker-accuracy fields (nullable, absent = not provided)
  final double? bboxX;
  final double? bboxY;
  final double? bboxW;
  final double? bboxH;
  final double? confidence;
  final double? correctedClickX;
  final double? correctedClickY;

  const ProductHotspot({
    required this.id,
    required this.x,
    required this.y,
    required this.itemType,
    required this.label,
    this.bboxX,
    this.bboxY,
    this.bboxW,
    this.bboxH,
    this.confidence,
    this.correctedClickX,
    this.correctedClickY,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'id': id,
      'x': x,
      'y': y,
      'itemType': itemType,
      'label': label,
    };
    if (bboxX != null) {
      map['bbox'] = {'x': bboxX, 'y': bboxY, 'w': bboxW, 'h': bboxH};
    }
    if (confidence != null) {
      map['confidence'] = confidence;
    }
    if (correctedClickX != null) {
      map['corrected_click_x'] = correctedClickX;
      map['corrected_click_y'] = correctedClickY;
    }
    return map;
  }

  factory ProductHotspot.fromJson(Map<String, dynamic> json) {
    // Parse optional bbox
    final bbox = json['bbox'] as Map<String, dynamic>?;
    double? bx, by, bw, bh;
    if (bbox != null) {
      bx = (bbox['x'] as num?)?.toDouble();
      by = (bbox['y'] as num?)?.toDouble();
      bw = (bbox['w'] as num?)?.toDouble();
      bh = (bbox['h'] as num?)?.toDouble();
    }

    return ProductHotspot(
      id: json['id'] as String,
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      itemType:
          json['itemType'] as String? ??
          json['item_type'] as String? ??
          json['furniture_type'] as String? ??
          'item',
      label: json['label'] as String? ?? 'Product',
      bboxX: bx,
      bboxY: by,
      bboxW: bw,
      bboxH: bh,
      confidence: (json['confidence'] as num?)?.toDouble(),
      correctedClickX: (json['corrected_click_x'] as num?)?.toDouble(),
      correctedClickY: (json['corrected_click_y'] as num?)?.toDouble(),
    );
  }

  @override
  String toString() {
    return 'ProductHotspot(id: $id, x: $x, y: $y, itemType: $itemType)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is ProductHotspot && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;
}
