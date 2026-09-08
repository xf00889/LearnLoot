from django.db import models
from django.utils import timezone

from courses.models import Course


class CoursePrice(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3)
    is_free = models.BooleanField(default=False)
    price_type = models.CharField(max_length=30, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)
    source_url = models.TextField(blank=True)

    class Meta:
        db_table = "course_prices"
        indexes = [
            models.Index(
                fields=("course", "observed_at"),
                name="course_prices_observed_idx",
            ),
            models.Index(
                fields=("course", "is_free", "observed_at"),
                name="course_prices_free_idx",
            ),
        ]
        ordering = ("-observed_at", "id")

    def __str__(self) -> str:
        if self.is_free:
            return f"{self.course}: Free"
        if self.amount is None:
            return f"{self.course}: Price unavailable"
        return f"{self.course}: {self.currency} {self.amount}"