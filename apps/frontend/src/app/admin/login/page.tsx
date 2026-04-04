import { LoginForm } from "@/features/admin-auth/ui/LoginForm";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export default function AdminLoginPage() {
  return (
    <div className="page-shell grid min-h-screen items-center py-10">
      <WindowFrame title="Admin" subtitle="Secure login">
        <div className="mx-auto max-w-md space-y-6">
          <h1 className="text-4xl font-semibold text-slate-900">Admin access</h1>
          <p className="text-slate-600">Use seeded credentials from the root `.env` file.</p>
          <LoginForm />
        </div>
      </WindowFrame>
    </div>
  );
}
