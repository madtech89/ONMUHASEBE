import React from 'react';
import { Menu, Globe, LogOut, User, Lock, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';

function getInitials(user) {
  if (!user) return '?';
  const first = user.first_name?.[0] || '';
  const last = user.last_name?.[0] || '';
  return (first + last).toUpperCase() || user.email?.[0]?.toUpperCase() || '?';
}

export default function Topbar({ onMenuClick }) {
  const { user, tenants, activeTenant, switchTenant, logout } = useAuth();
  const { language, switchLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
    toast.success('Çıkış yapıldı');
  };

  return (
    <header
      className="h-16 flex items-center justify-between px-4 bg-white border-b border-border shadow-sm z-10 flex-shrink-0"
      data-testid="topbar"
    >
      {/* Left: menu toggle + tenant badge */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost" size="icon"
          onClick={onMenuClick}
          data-testid="topbar-menu-btn"
          className="lg:hidden"
        >
          <Menu size={20} />
        </Button>

        {/* Tenant switcher */}
        {activeTenant && (
          tenants.length > 1 ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-1.5 h-8 text-sm" data-testid="tenant-switcher-dropdown">
                  <span className="w-2 h-2 rounded-full bg-primary" />
                  <span className="font-medium">{activeTenant.name}</span>
                  <ChevronDown size={14} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                {tenants.map(t => (
                  <DropdownMenuItem key={t.public_id} onClick={() => switchTenant(t)}>
                    {t.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Badge variant="outline" className="gap-1.5 text-sm py-1" data-testid="tenant-badge">
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              {activeTenant.name}
            </Badge>
          )
        )}
      </div>

      {/* Right: lang + user menu */}
      <div className="flex items-center gap-2">
        {/* Language toggle */}
        <Button
          variant="ghost" size="sm"
          onClick={() => switchLanguage(language === 'tr' ? 'en' : 'tr')}
          data-testid="lang-toggle-btn"
          className="gap-1.5 text-xs font-semibold text-muted-foreground"
        >
          <Globe size={15} />
          {language.toUpperCase()}
        </Button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 h-9 px-2" data-testid="user-menu-btn">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">
                {getInitials(user)}
              </div>
              <div className="hidden sm:flex flex-col items-start text-left">
                <span className="text-sm font-medium leading-tight">{user?.first_name || user?.email?.split('@')[0]}</span>
                <span className="text-[10px] text-muted-foreground leading-tight">
                  {user?.is_super_admin ? 'Super Admin' : activeTenant?.name || ''}
                </span>
              </div>
              <ChevronDown size={14} className="text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <div className="px-3 py-2">
              <p className="text-sm font-medium">{user?.full_name || user?.email}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate('/security')} data-testid="user-menu-security">
              <Lock size={14} className="mr-2" /> {t('nav.security')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive" data-testid="user-menu-logout">
              <LogOut size={14} className="mr-2" /> {t('auth.logout')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
