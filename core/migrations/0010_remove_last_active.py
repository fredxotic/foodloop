from django.db import migrations


def remove_last_active_column(apps, schema_editor):
    """Drop last_active column if it exists"""
    with schema_editor.connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user_profiles' 
            AND column_name='last_active';
        """)
        
        if cursor.fetchone():
            print(" Found last_active column - dropping it...")
            cursor.execute("""
                ALTER TABLE user_profiles 
                DROP COLUMN last_active CASCADE;
            """)
            print(" Dropped last_active column")
        else:
            print(" last_active column does not exist")


def reverse_remove(apps, schema_editor):
    """Reverse migration (do nothing)"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0009_remove_phone_verified_column'),
    ]
    
    operations = [
        migrations.RunPython(
            remove_last_active_column,
            reverse_code=reverse_remove
        ),
    ]