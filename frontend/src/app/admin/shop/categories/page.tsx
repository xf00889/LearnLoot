"use client";

import { CategoryManager } from "@/components/admin/category-manager";

export default function AffiliateCategoriesPage() {
  return <CategoryManager scope="affiliate" title="Affiliate categories" description="Create categories for affiliate posts and products, then select them while editing content." />;
}
