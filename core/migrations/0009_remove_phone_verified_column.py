from django.db import migrations


def drop_phone_verified_column(apps, schema_editor):
    """Drop phone_verified column if it exists"""
    with schema_editor.connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user_profiles' 
            AND column_name='phone_verified';
        """)
        
        if cursor.fetchone():
            print("⚠️  Found phone_verified column - dropping it...")
            cursor.execute("""
                ALTER TABLE user_profiles 
                DROP COLUMN IF EXISTS phone_verified;
            """)
            print("✅ Dropped phone_verified column")
        else:
            print("ℹ️  phone_verified column does not exist (already dropped)")


def reverse_drop(apps, schema_editor):
    """Reverse: add phone_verified column back"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE user_profiles 
            ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
        """)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_cleanup_phone_numbers'),
    ]
    
    operations = [
        migrations.RunPython(
            drop_phone_verified_column,
            reverse_code=reverse_drop
        ),
    ]