// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/Ownable.sol";

// Interface for our test tokens (compatible with OpenZeppelin ERC20)
interface ITestToken {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function mint(uint256 amount) external;
    function mintTo(address to, uint256 amount) external;
}

/**
 * @title TestRemittanceBridge
 * @dev A simplified remittance bridge for testing remittance flows with test tokens
 */
contract TestRemittanceBridge is Ownable {
    ITestToken public tUsdToken;
    ITestToken public tEurToken;
    
    // Exchange rate variables (with 6 decimal precision)
    uint256 public usdToEurRate = 900000; // 0.9 EUR per USD (example rate)
    
    // Fee settings (basis points, 1 bp = 0.01%)
    uint256 public feeRate = 50; // 0.5% fee
    address public feeCollector;
    
    // Track costs for each remittance
    struct RemittanceCost {
        uint256 usdcToUsdRate;  // Rate for converting USD to USDC (1:1 assumed)
        uint256 usdcToEurcRate; // Rate for converting USDC to EURC
        uint256 eurcToEurRate;  // Rate for converting EURC to EUR (1:1 assumed)
        uint256 networkFee;     // Estimated network fee (gas)
        uint256 serviceFee;     // Service fee for the remittance
        uint256 totalCostUsd;   // Total cost in USD
    }
    
    mapping(address => RemittanceCost[]) public userRemittanceCosts;
    
    // Events for tracking
    event RemittanceProcessed(
        address indexed sender,
        uint256 tUsdAmount,
        uint256 tEurAmount,
        string recipient
    );
    
    event RemittanceCostRecorded(
        address indexed user,
        uint256 usdcToUsdRate,
        uint256 usdcToEurcRate,
        uint256 eurcToEurRate,
        uint256 networkFee,
        uint256 serviceFee,
        uint256 totalCostUsd
    );
    
    event RateUpdated(uint256 newRate);
    event FeeRateUpdated(uint256 newFeeRate);
    
    /**
     * @dev Constructor sets the token addresses and owner
     * @param _tUsdAddress The address of the tUSD token contract
     * @param _tEurAddress The address of the tEUR token contract
     * @param _feeCollector The address that will receive the fees
     */
    constructor(address _tUsdAddress, address _tEurAddress, address _feeCollector) 
        Ownable(msg.sender) 
    {
        tUsdToken = ITestToken(_tUsdAddress);
        tEurToken = ITestToken(_tEurAddress);
        feeCollector = _feeCollector;
    }
    
    /**
     * @dev Updates the exchange rate (owner only)
     * @param _newRate The new USD to EUR exchange rate (with 6 decimal precision)
     */
    function updateExchangeRate(uint256 _newRate) external onlyOwner {
        require(_newRate > 0, "TestRemittanceBridge: rate must be greater than zero");
        usdToEurRate = _newRate;
        emit RateUpdated(_newRate);
    }
    
    /**
     * @dev Updates the fee rate (owner only)
     * @param _newFeeRate The new fee rate in basis points
     */
    function updateFeeRate(uint256 _newFeeRate) external onlyOwner {
        require(_newFeeRate <= 500, "TestRemittanceBridge: fee cannot exceed 5%");
        feeRate = _newFeeRate;
        emit FeeRateUpdated(_newFeeRate);
    }
    
    /**
     * @dev Calculates the amount of tEUR to receive based on tUSD amount
     * @param _tUsdAmount The amount of tUSD to convert
     * @return The amount of tEUR that will be received
     */
    function calculateTEurAmount(uint256 _tUsdAmount) public view returns (uint256) {
        // Calculate the tEUR amount based on the exchange rate
        uint256 tEurBeforeFee = (_tUsdAmount * usdToEurRate) / 1000000;
        
        // Calculate and subtract the fee
        uint256 fee = (tEurBeforeFee * feeRate) / 10000;
        return tEurBeforeFee - fee;
    }
    
    /**
     * @dev Gets test tokens and then converts from tUSD to tEUR in one transaction
     * @param _tUsdAmount The amount of tUSD to convert
     * @param _recipient String identifier for the recipient
     * @return The amount of tEUR that was sent
     */
    function processRemittance(uint256 _tUsdAmount, string memory _recipient) external returns (uint256) {
        require(_tUsdAmount > 0, "TestRemittanceBridge: amount must be greater than zero");
        
        // Calculate the tEUR amount
        uint256 tEurAmount = calculateTEurAmount(_tUsdAmount);
        
        // First, mint tUSD directly to the sender (for testing convenience)
        tUsdToken.mintTo(msg.sender, _tUsdAmount);
        
        // Then transfer the tUSD from sender to this contract
        require(
            tUsdToken.transferFrom(msg.sender, address(this), _tUsdAmount),
            "TestRemittanceBridge: tUSD transfer failed"
        );
        
        // Calculate the fee
        uint256 fee = (_tUsdAmount * feeRate) / 10000;
        
        // Transfer fee to fee collector
        if (fee > 0) {
            tUsdToken.transfer(feeCollector, fee);
        }
        
        // Mint tEUR directly to the sender
        tEurToken.mintTo(msg.sender, tEurAmount);
        
        emit RemittanceProcessed(msg.sender, _tUsdAmount, tEurAmount, _recipient);
        
        return tEurAmount;
    }
    
    /**
     * @dev Record the cost of a remittance transaction
     * @param _user The user who performed the remittance
     * @param _networkFee Estimated network fee in USD (gas costs)
     * @param _serviceFee Service fee for the remittance
     */
    function recordRemittanceCost(
        address _user,
        uint256 _networkFee,
        uint256 _serviceFee
    ) external onlyOwner {
        // Use 1:1 rate for USD to USDC and EURC to EUR for simplicity
        uint256 usdcToUsdRate = 1000000; // 1:1 (6 decimals)
        uint256 eurcToEurRate = 1000000; // 1:1 (6 decimals)
        
        uint256 totalCost = _networkFee + _serviceFee;
        
        RemittanceCost memory cost = RemittanceCost({
            usdcToUsdRate: usdcToUsdRate,
            usdcToEurcRate: usdToEurRate,
            eurcToEurRate: eurcToEurRate,
            networkFee: _networkFee,
            serviceFee: _serviceFee,
            totalCostUsd: totalCost
        });
        
        userRemittanceCosts[_user].push(cost);
        
        emit RemittanceCostRecorded(
            _user,
            usdcToUsdRate,
            usdToEurRate,
            eurcToEurRate,
            _networkFee,
            _serviceFee,
            totalCost
        );
    }
    
    /**
     * @dev Get the latest remittance cost for a user
     * @param _user The user to query
     * @return The latest remittance cost details
     */
    function getLatestRemittanceCost(address _user) external view returns (
        uint256 usdcToUsdRate,
        uint256 usdcToEurcRate,
        uint256 eurcToEurRate,
        uint256 networkFee,
        uint256 serviceFee,
        uint256 totalCostUsd
    ) {
        require(userRemittanceCosts[_user].length > 0, "TestRemittanceBridge: no remittance costs recorded");
        
        RemittanceCost memory latest = userRemittanceCosts[_user][userRemittanceCosts[_user].length - 1];
        
        return (
            latest.usdcToUsdRate,
            latest.usdcToEurcRate,
            latest.eurcToEurRate,
            latest.networkFee,
            latest.serviceFee,
            latest.totalCostUsd
        );
    }
    
    /**
     * @dev Get the number of remittance costs recorded for a user
     * @param _user The user to query
     * @return The number of remittance costs recorded
     */
    function getRemittanceCostCount(address _user) external view returns (uint256) {
        return userRemittanceCosts[_user].length;
    }
    
    /**
     * @dev Set a new fee collector address
     * @param _newFeeCollector The new fee collector address
     */
    function setFeeCollector(address _newFeeCollector) external onlyOwner {
        require(_newFeeCollector != address(0), "TestRemittanceBridge: fee collector cannot be zero address");
        feeCollector = _newFeeCollector;
    }
    
    /**
     * @dev Allows the owner to withdraw any tokens from the contract in case of emergency
     * @param _token The address of the token to withdraw
     * @param _amount The amount to withdraw
     */
    function emergencyWithdraw(address _token, uint256 _amount) external onlyOwner {
        ITestToken token = ITestToken(_token);
        require(
            token.transfer(owner(), _amount),
            "TestRemittanceBridge: Emergency withdrawal failed"
        );
    }
} 