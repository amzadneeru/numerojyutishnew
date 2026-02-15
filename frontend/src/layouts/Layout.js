import React from 'react';
import Header from '../components/Header';
import Footer from '../components/Footer';

function Layout({ children }) {
  return (
    <>
      <Header />
      <main className="layout-main">
        {children}
      </main>
      <Footer />
    </>
  );
}

export default Layout;
