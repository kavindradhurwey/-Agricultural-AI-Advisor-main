"""
Setup script to create a default user account for testing
Creates user with username 'farmer' and password 'agri1234'
"""

from database_manager import DatabaseManager

def setup_default_user():
    """Create default user account for testing"""
    db_manager = DatabaseManager()
    
    # Create default user
    username = "farmer"
    password = "agri1234"
    
    success, message = db_manager.create_user(username, password)
    
    if success:
        print("SUCCESS: Default user created successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
        
        # Get user ID and create a sample profile
        auth_success, user_id = db_manager.authenticate_user(username, password)
        if auth_success:
            # Create a sample profile
            sample_profile = {
                'name': 'Test Farmer',
                'location': 'Wardha, Maharashtra',
                'farm_size': 3.0,
                'primary_crops': ['Cotton', 'Wheat'],
                'farming_type': 'Traditional',
                'experience': 10,
                'preferred_language': 'English',
                'notification_preferences': ['Weather Updates', 'Market Prices'],
                'interests': ['Crop Diseases', 'Financial Planning']
            }
            
            if db_manager.save_user_profile(user_id, sample_profile):
                print("SUCCESS: Sample profile created successfully!")
            else:
                print("WARNING: Profile creation failed")
    else:
        if "already exists" in message:
            print(f"INFO: User '{username}' already exists - you can use it directly")
            print(f"Username: {username}")
            print(f"Password: {password}")
        else:
            print(f"ERROR: Error creating user: {message}")

if __name__ == "__main__":
    setup_default_user()
