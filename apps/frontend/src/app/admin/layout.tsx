import { AdminLayoutShell } from "@/widgets/admin/ui/AdminLayoutShell";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminLayoutShell>{children}</AdminLayoutShell>;
}

