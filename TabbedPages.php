<?php

abstract class TabbedPage extends HTML_QuickForm2_Controller_Page
{
    protected function addTabs()
    {
        $tabGroup = $this->form->addElement('group')->setSeparator('&nbsp;')
                               ->setId('tabs');
        foreach ($this->getController() as $pageId => $page) {
            $tabGroup->addElement('submit', $this->getButtonName($pageId),
                                  array('class' => 'flat', 'value' => ucfirst($pageId)) +
                                  ($page === $this? array('disabled' => 'disabled'): array()));
        }
    }

    protected function addGlobalSubmit()
    {
        $this->form->addElement('submit', $this->getButtonName('submit'),
                                array('value' => 'Global Submit', 'class' => 'bigred'));
        $this->setDefaultAction('submit', 'empty.gif');
    }
}

/****************************************************************** 
USAGE

class PageFoo extends TabbedPage
{
    	protected function populateForm()
    	{
        	$this->addTabs();
		//...  ADD ELEMENTS, RULES, etc
	 	$this->addGlobalSubmit();
	}
}



$tabbed = new HTML_QuickForm2_Controller('Tabbed', false);
$tabbed->addPage(new PageFoo(new HTML_QuickForm2('foo')));
$tabbed->addPage(new PageBar(new HTML_QuickForm2('bar')));
// These actions manage going directly to the pages with the same name
$tabbed->addHandler('foo', new HTML_QuickForm2_Controller_Action_Direct());
$tabbed->addHandler('bar', new HTML_QuickForm2_Controller_Action_Direct());
// We actually add these handlers here for the sake of example
// They can be automatically loaded and added by the controller
$tabbed->addHandler('submit', new HTML_QuickForm2_Controller_Action_Submit());
$tabbed->addHandler('jump', new HTML_QuickForm2_Controller_Action_Jump());
// This is the action we should always define ourselves
$tabbed->addHandler('process', new ActionProcess());
// We redefine 'display' handler to use the proper stylesheets
$tabbed->addHandler('display', new QF2_ActionDisplay());

************************************************************************/
?>
