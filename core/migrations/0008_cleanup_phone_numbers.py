from django.db import migrations, models
import core.validators


def cleanup_duplicate_phones(apps, schema_editor):
    """Remove duplicate NULL phone numbers and drop unique constraints"""
    with schema_editor.connection.cursor() as cursor:
        # 1. Drop ALL unique constraints/indexes on phone_number
        cursor.execute("""
            DROP INDEX IF EXISTS user_profiles_phone_number_ef2c3933_uniq CASCADE;
            DROP INDEX IF EXISTS user_profiles_phone_number_key CASCADE;
        """)
        print("✅ Dropped all phone_number unique constraints")
        
        # 2. Set all empty string phone numbers to NULL
        cursor.execute("""
            UPDATE user_profiles 
            SET phone_number = NULL 
            WHERE phone_number = '' OR phone_number IS NULL;
        """)
        print("✅ Cleaned up empty phone numbers")
        
        # 3. ✅ FIX: Remove NOT NULL constraint (PostgreSQL correct syntax)
        # Check if column has NOT NULL constraint first
        cursor.execute("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'user_profiles' 
            AND column_name = 'phone_number';
        """)
        
        result = cursor.fetchone()
        if result and result[0] == 'NO':
            # Column has NOT NULL constraint, remove it
            cursor.execute("""
                ALTER TABLE user_profiles 
                ALTER COLUMN phone_number DROP NOT NULL;
            """)
            print("✅ Removed NOT NULL constraint from phone_number")
        else:
            print("ℹ️  phone_number already allows NULL")


def reverse_cleanup(apps, schema_editor):
    """Reverse migration (do nothing critical)"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_fix_duplicate_phones'),
    ]
    
    operations = [
        migrations.RunPython(cleanup_duplicate_phones, reverse_cleanup),
        
        # Remove unique=True from model
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(
                max_length=15,
                blank=True,
                null=True,
                unique=False, 
                validators=[core.validators.validate_phone_number]
            ),
        ),
    ]