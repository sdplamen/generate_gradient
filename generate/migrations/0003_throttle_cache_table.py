from django.core.management import call_command
from django.db import migrations


def create_cache_tables(apps, schema_editor):
    """Create the table of the database cache that holds API throttle counts (settings.CACHES['throttle'])."""
    call_command('createcachetable', database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0002_palette_name'),
    ]

    operations = [
        migrations.RunPython(create_cache_tables, migrations.RunPython.noop),
    ]
