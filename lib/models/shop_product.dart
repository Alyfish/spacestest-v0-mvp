/// Model for a product in the shopping/product selection screens
class ShopProduct {
  final String id;
  final String name;
  final String description;
  final double price;
  final String retailerName;
  final String? retailerLogoUrl;
  final String imageUrl;
  final String? color;
  final String? category;

  const ShopProduct({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.retailerName,
    this.retailerLogoUrl,
    required this.imageUrl,
    this.color,
    this.category,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'price': price,
      'retailerName': retailerName,
      'retailerLogoUrl': retailerLogoUrl,
      'imageUrl': imageUrl,
      'color': color,
      'category': category,
    };
  }

  factory ShopProduct.fromJson(Map<String, dynamic> json) {
    return ShopProduct(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      price: (json['price'] as num).toDouble(),
      retailerName: json['retailerName'] as String? ?? 'Unknown',
      retailerLogoUrl: json['retailerLogoUrl'] as String?,
      imageUrl: json['imageUrl'] as String? ?? '',
      color: json['color'] as String?,
      category: json['category'] as String?,
    );
  }

  ShopProduct copyWith({
    String? id,
    String? name,
    String? description,
    double? price,
    String? retailerName,
    String? retailerLogoUrl,
    String? imageUrl,
    String? color,
    String? category,
  }) {
    return ShopProduct(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      price: price ?? this.price,
      retailerName: retailerName ?? this.retailerName,
      retailerLogoUrl: retailerLogoUrl ?? this.retailerLogoUrl,
      imageUrl: imageUrl ?? this.imageUrl,
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
}

/// Model for a hotspot/marker on the generated dream space image
class ProductHotspot {
  final String id;
  final double x; // Position as percentage (0-1)
  final double y; // Position as percentage (0-1)
  final String itemType; // 'couch', 'lamp', 'vase', etc.
  final String label;

  const ProductHotspot({
    required this.id,
    required this.x,
    required this.y,
    required this.itemType,
    required this.label,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'x': x,
      'y': y,
      'itemType': itemType,
      'label': label,
    };
  }

  factory ProductHotspot.fromJson(Map<String, dynamic> json) {
    return ProductHotspot(
      id: json['id'] as String,
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      itemType: json['itemType'] as String? ?? 'item',
      label: json['label'] as String? ?? 'Product',
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
