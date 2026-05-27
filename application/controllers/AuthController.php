<?php

//http://framework.zend.com/manual/en/learning.multiuser.authentication.html

      class AuthController extends Zend_Controller_Action
      {
          public function loginAction()
          {
              $db = $this->_getParam('db');
       
              $loginForm = new Default_Form_Auth_Login();
       
              if ($loginForm->isValid($_POST)) {
       
                  $adapter = new Zend_Auth_Adapter_DbTable(
                      $db,
                      'users',
                      'username',
                      'password',
                      'MD5(CONCAT(?, password_salt))'
                      );
       
                  $adapter->setIdentity($loginForm->getValue('username'));
                  $adapter->setCredential($loginForm->getValue('password'));
       
                  $auth   = Zend_Auth::getInstance();
                  $result = $auth->authenticate($adapter);
       
                  if ($result->isValid()) {
                      $this->_helper->FlashMessenger('Successful Login');
                      $this->_redirect('/');
                      return;
                  }
       
              }
       
              $this->view->loginForm = $loginForm;
       
          }
       
      }
?>
