'use my-client'; // client component
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Users, FileSpreadsheet } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    {
      href: '/',
      label: 'Patient Census',
      icon: Users,
      active: pathname === '/' || pathname.startsWith('/census')
    },
    {
      href: '/patient/demo-001',
      label: 'Patient State',
      icon: Activity,
      active: pathname.startsWith('/patient')
    }
  ];

  return (
    <aside className="w-64 border-r border-border bg-sidebar select-none shrink-0 flex flex-col h-screen sticky top-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-border bg-[#050b14]/50">
        <Link href="/" className="flex items-center gap-2">
          <Activity className="size-5 text-[#00f3ff] animate-pulse" />
          <span className="text-sm font-bold bg-gradient-to-r from-white to-[#00ff9d] bg-clip-text text-transparent font-mono tracking-wider">
            MSIGNALS ICU
          </span>
        </Link>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-semibold tracking-wide transition-all duration-100",
                item.active
                  ? "bg-secondary text-[#00f3ff] shadow-sm border border-border"
                  : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
              )}
            >
              <Icon className="size-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Branding */}
      <div className="p-4 border-t border-border bg-[#050b14]/30 text-[10px] text-muted-foreground/60 text-center font-mono">
        ALI MAS Platform &copy; 2026
      </div>
    </aside>
  );
}
