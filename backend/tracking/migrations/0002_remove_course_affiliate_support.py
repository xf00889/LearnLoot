# Generated for LearnLoot Phase 9A.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tracking", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="clickevent",
            name="affiliate_link",
        ),
        migrations.RemoveField(
            model_name="clickevent",
            name="destination_kind",
        ),
        migrations.DeleteModel(
            name="AffiliateLink",
        ),
    ]
