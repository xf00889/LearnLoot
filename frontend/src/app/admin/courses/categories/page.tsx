"use client";

import { CategoryManager } from "@/components/admin/category-manager";

export default function CourseCategoriesPage() {
  return <CategoryManager scope="course" title="Course categories" description="Create the taxonomy used by courses. Automated discovery never assigns a category; editors choose one manually." />;
}
