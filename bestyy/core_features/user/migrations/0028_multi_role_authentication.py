# Generated migration for multi-role authentication

from django.db import migrations, models
import django.db.models.deletion


def populate_usernames(apps, schema_editor):
    """Populate username field for existing users"""
    User = apps.get_model('user', 'User')
    for user in User.objects.all():
        if not user.username:
            user.username = f"{user.email}_{user.role}"
            user.save(update_fields=['username'])


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0027_anonymouscart_and_more'),
    ]

    operations = [
        # Step 1: Add username field without unique constraint
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        # Step 2: Populate usernames for existing users
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
        # Step 3: Make username non-null and unique
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(blank=True, max_length=255, unique=True),
        ),
        # Step 4: Remove unique constraint from PendingUser email
        migrations.AlterField(
            model_name='pendinguser',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        # Step 5: Make email non-unique on User
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(db_index=True, verbose_name='email address'),
        ),
        # Step 6: Add unique constraint on email+role
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(fields=('email', 'role'), name='unique_email_role'),
        ),
    ]
