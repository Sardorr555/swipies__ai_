import { Navigate, Outlet } from 'react-router';
import authorizationUtil from '@/utils/authorization-util';

export default function AdminAuthorizedLayout() {
  const hasAuth = !!authorizationUtil.getAuthorization();

  return hasAuth ? <Outlet /> : <Navigate to="/admin/login" replace />;
}
