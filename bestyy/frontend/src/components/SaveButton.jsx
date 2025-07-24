import React from 'react';
import 'font-awesome/css/font-awesome.min.css';
import './SaveButton.css';

const SaveButton = ({ onClick }) => (
  <button className="save-btn" onClick={onClick}>
    <span className="icon-square">
      <i className="fa fa-save"></i>
    </span>
    <span className="save-text">Save Changes</span>
  </button>
);

export default SaveButton; 