from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

recommendations_data = {}
user_mappings = {}
product_mappings = {}
model_metrics = {}

def load_csv_from_spark_output(csv_dir_path):
    """Load CSV data from Spark output directory (contains part files)"""
    import glob
    
    logger.info(f"load_csv_from_spark_output called with: {csv_dir_path}")
    
    if not os.path.exists(csv_dir_path):
        logger.info(f"Path does not exist: {csv_dir_path}")
        return None
    
    if not os.path.isdir(csv_dir_path):
        logger.warning(f"Path is not a directory: {csv_dir_path}")
        return None
    
    part_files = glob.glob(os.path.join(csv_dir_path, "part-*.csv"))
    logger.info(f"Found {len(part_files)} part files: {part_files}")
    
    if not part_files:
        logger.warning(f"No part files found in {csv_dir_path}")
        return None
    
    dataframes = []
    for part_file in part_files:
        try:
            logger.info(f"Reading part file: {part_file}")
            df = pd.read_csv(part_file)
            logger.info(f"Loaded {len(df)} rows from {part_file}")
            dataframes.append(df)
        except Exception as e:
            logger.warning(f"Could not read part file {part_file}: {e}")
            continue
    
    if not dataframes:
        logger.warning("No dataframes loaded from part files")
        return None
    
    combined_df = pd.concat(dataframes, ignore_index=True)
    logger.info(f"Combined dataframe shape: {combined_df.shape}")
    return combined_df

def load_recommendation_data():
    """Load recommendation data from CSV files"""
    global recommendations_data, user_mappings, product_mappings, model_metrics
    
    try:
        results_path = "/app/results"
        logger.info(f"Loading data from {results_path}")
        
        recommendations_path = os.path.join(results_path, "recommendations.csv")
        logger.info(f"Trying to load recommendations from {recommendations_path}")
        recommendations_df = load_csv_from_spark_output(recommendations_path)
        
        if recommendations_df is not None and not recommendations_df.empty:
            logger.info(f"Loaded {len(recommendations_df)} detailed recommendations")
            
            # Group recommendations by user (using original user names)
            recommendations_data = {}
            for _, row in recommendations_df.iterrows():
                user = str(row['user'])  # Ensure user is string
                if user not in recommendations_data:
                    recommendations_data[user] = []
                recommendations_data[user].append({
                    'product': str(row['product']),
                    'product_id': int(row['productId']),
                    'score': float(row['score'])
                })
            
            for user in recommendations_data:
                recommendations_data[user].sort(key=lambda x: x['score'], reverse=True)
                
        else:
            edges_path = os.path.join(results_path, "edges.csv")
            logger.info(f"Trying to load edges from {edges_path}")
            edges_df = load_csv_from_spark_output(edges_path)
            
            if edges_df is not None and not edges_df.empty:
                logger.info(f"Loaded {len(edges_df)} recommendation edges (fallback)")
                
                recommendations_data = {}
                for _, row in edges_df.iterrows():
                    user_id = str(row['src']) 
                    product_id = int(row['dst'])
                    
                    if user_id not in recommendations_data:
                        recommendations_data[user_id] = []
                    
                    recommendations_data[user_id].append({
                        'product_id': product_id,
                        'product': f'product{product_id}' 
                    })
            else:
                logger.warning("No recommendation data found")
                recommendations_data = {}
        
        user_mappings_path = os.path.join(results_path, "user_mappings.csv")
        user_mappings_df = load_csv_from_spark_output(user_mappings_path)
        if user_mappings_df is not None and not user_mappings_df.empty:
            user_mappings = dict(zip(user_mappings_df['userId'], user_mappings_df['user']))
            
        product_mappings_path = os.path.join(results_path, "product_mappings.csv")
        product_mappings_df = load_csv_from_spark_output(product_mappings_path)
        if product_mappings_df is not None and not product_mappings_df.empty:
            product_mappings = dict(zip(product_mappings_df['productId'], product_mappings_df['product']))
        
        rmse_path = os.path.join(results_path, "rmse.txt")
        if os.path.exists(rmse_path):
            with open(rmse_path, 'r') as f:
                content = f.read().strip()
                if content.startswith("RMSE:"):
                    model_metrics['rmse'] = float(content.split(":")[1].strip())
        
        logger.info(f"Loaded recommendations for {len(recommendations_data)} users")
        logger.info(f"Available users: {list(recommendations_data.keys())[:10]}")  # Log first 10 users
        return True
        
    except Exception as e:
        logger.error(f"Error loading recommendation data: {str(e)}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "users_with_recommendations": len(recommendations_data)
    })

@app.route('/recommendations/<user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    """Get recommendations for a specific user"""
    try:
        load_recommendation_data()
        
        limit = request.args.get('limit', 5, type=int)
        
        if user_id not in recommendations_data:
            return jsonify({
                "error": f"No recommendations found for user {user_id}",
                "user_id": user_id,
                "available_users": list(recommendations_data.keys())[:10]  # Show first 10 available users
            }), 404
        
        recommendations = recommendations_data[user_id][:limit]
        
        return jsonify({
            "user_id": user_id,
            "recommendations": recommendations,
            "count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/recommendations', methods=['POST'])
def get_multiple_user_recommendations():
    """Get recommendations for multiple users"""
    try:
        data = request.get_json()
        if not data or 'user_ids' not in data:
            return jsonify({"error": "user_ids field is required"}), 400
        
        user_ids = data['user_ids']
        limit = data.get('limit', 5)
        
        load_recommendation_data()
        
        results = {}
        for user_id in user_ids:
            if user_id in recommendations_data:
                results[user_id] = recommendations_data[user_id][:limit]
            else:
                results[user_id] = []
        
        return jsonify({
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "total_users_requested": len(user_ids),
            "users_with_recommendations": len([uid for uid in user_ids if uid in recommendations_data])
        })
        
    except Exception as e:
        logger.error(f"Error getting multiple user recommendations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    """Get list of users with recommendations"""
    try:
        load_recommendation_data()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        user_ids = list(recommendations_data.keys())
        total_users = len(user_ids)
        
        # Pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_users = user_ids[start_idx:end_idx]
        
        return jsonify({
            "users": paginated_users,
            "total_users": total_users,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_users + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/users/<user_id>/similar', methods=['GET'])
def get_similar_users(user_id):
    """Find users with similar recommendation patterns"""
    try:
        load_recommendation_data()
        
        if user_id not in recommendations_data:
            return jsonify({"error": f"User {user_id} not found"}), 404
        
        # Get product IDs for the user
        user_products = set()
        for rec in recommendations_data[user_id]:
            if 'product_id' in rec:
                user_products.add(rec['product_id'])
            elif 'product' in rec:
                user_products.add(rec['product'])
        
        limit = request.args.get('limit', 10, type=int)
        
        similarities = []
        for other_user_id, other_recommendations in recommendations_data.items():
            if other_user_id != user_id:
                other_products = set()
                for rec in other_recommendations:
                    if 'product_id' in rec:
                        other_products.add(rec['product_id'])
                    elif 'product' in rec:
                        other_products.add(rec['product'])
                
                common_products = len(user_products & other_products)
                if common_products > 0:
                    similarity = common_products / len(user_products | other_products)
                    similarities.append({
                        "user_id": other_user_id,
                        "similarity_score": similarity,
                        "common_products": common_products,
                        "common_product_ids": list(user_products & other_products)
                    })
        
        # Sort by similarity score
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return jsonify({
            "user_id": user_id,
            "similar_users": similarities[:limit],
            "total_similar_users": len(similarities)
        })
        
    except Exception as e:
        logger.error(f"Error finding similar users for {user_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/products/<product_id>/users', methods=['GET'])
def get_users_for_product(product_id):
    """Get users who have this product in their recommendations"""
    try:
        load_recommendation_data()
        
        limit = request.args.get('limit', 20, type=int)
        
        users_with_product = []
        for user_id, recommendations in recommendations_data.items():
            for idx, rec in enumerate(recommendations):
                # Check both product_id and product name
                if (isinstance(rec, dict) and 
                    (('product_id' in rec and str(rec['product_id']) == str(product_id)) or
                     ('product' in rec and str(rec['product']) == str(product_id)))):
                    users_with_product.append({
                        "user_id": user_id,
                        "recommendation_rank": idx + 1,
                        "score": rec.get('score', 0)
                    })
                    break
                elif not isinstance(rec, dict) and str(rec) == str(product_id):
                    users_with_product.append({
                        "user_id": user_id,
                        "recommendation_rank": idx + 1
                    })
                    break
        
        users_with_product.sort(key=lambda x: x['recommendation_rank'])
        
        return jsonify({
            "product_id": product_id,
            "users": users_with_product[:limit],
            "total_users": len(users_with_product)
        })
        
    except Exception as e:
        logger.error(f"Error getting users for product {product_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_recommendation_stats():
    """Get overall recommendation statistics"""
    try:
        load_recommendation_data()
        
        total_users = len(recommendations_data)
        total_recommendations = sum(len(recs) for recs in recommendations_data.values())
        
        all_products = set()
        for recommendations in recommendations_data.values():
            for rec in recommendations:
                if isinstance(rec, dict):
                    if 'product_id' in rec:
                        all_products.add(rec['product_id'])
                    elif 'product' in rec:
                        all_products.add(rec['product'])
                else:
                    all_products.add(rec)
        
        avg_recommendations = total_recommendations / total_users if total_users > 0 else 0
        
        product_counts = {}
        for recommendations in recommendations_data.values():
            for rec in recommendations:
                if isinstance(rec, dict):
                    product_key = rec.get('product_id') or rec.get('product')
                else:
                    product_key = rec
                    
                if product_key:
                    product_counts[product_key] = product_counts.get(product_key, 0) + 1
        
        top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        stats = {
            "total_users": total_users,
            "total_unique_products": len(all_products),
            "total_recommendations": total_recommendations,
            "average_recommendations_per_user": round(avg_recommendations, 2),
            "top_recommended_products": [{"product_id": pid, "recommendation_count": count} for pid, count in top_products],
            "model_metrics": model_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reload', methods=['POST'])
def reload_data():
    """Manually reload recommendation data"""
    try:
        success = load_recommendation_data()
        if success:
            return jsonify({
                "message": "Data reloaded successfully",
                "users_loaded": len(recommendations_data),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Failed to reload data"}), 500
            
    except Exception as e:
        logger.error(f"Error reloading data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Load initial data
    load_recommendation_data()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
