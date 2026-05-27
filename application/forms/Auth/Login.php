<?php
//http://framework.zend.com/manual/en/learning.multiuser.authentication.html
      // located at application/forms/Auth/Login.php
       
      class Default_Form_Auth_Login extends Zend_Form
      {
          public function init()
          {
              $this->setMethod('post');
       
              $this->addElement(
                  'text', 'username', array(
                      'label' => 'Username:',
                      'required' => true,
                      'filters'    => array('StringTrim'),
                  ));
       
              $this->addElement('password', 'password', array(
                  'label' => 'Password:',
                  'required' => true,
                  ));
       
              $this->addElement('submit', 'submit', array(
                  'ignore'   => true,
                  'label'    => 'Login',
                  ));
       
          }
      }

?>
